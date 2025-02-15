import torch
import torch.nn as nn
import torch.nn.functional as F

# source from https://github.com/SeanNaren/deepspeech.pytorch/blob/master/deepspeech_pytorch/model.py


class SequenceWise(nn.Module):
    def __init__(self, module):
        """
        Collapses input of dim T*N*H to (T*N)*H, and applies to a module.
        Allows handling of variable sequence lengths and minibatch sizes.
        :param module: Module to apply input to.
        """
        super(SequenceWise, self).__init__()
        self.module = module

    def forward(self, x):
        t, n = x.size(0), x.size(1)
        x = x.view(t * n, -1)
        x = self.module(x)
        x = x.view(t, n, -1)
        return x

    def __repr__(self):
        tmpstr = self.__class__.__name__ + " (\n"
        tmpstr += self.module.__repr__()
        tmpstr += ")"
        return tmpstr


class MaskConv(nn.Module):
    def __init__(self, seq_module):
        """
        Adds padding to the output of the module based on the given lengths. This is to ensure that the
        results of the model do not change when batch sizes change during inference.
        Input needs to be in the shape of (BxCxDxT)
        :param seq_module: The sequential module containing the conv stack.
        """
        super(MaskConv, self).__init__()
        self.seq_module = seq_module

    def forward(self, x, lengths):
        """
        :param x: The input of size BxCxDxT
        :param lengths: The actual length of each sequence in the batch
        :return: Masked output from the module
        """
        for module in self.seq_module:
            x = module(x)
            mask = torch.BoolTensor(x.size()).fill_(0)
            if x.is_cuda:
                mask = mask.cuda()
            for i, length in enumerate(lengths):
                length = length.item()
                if (mask[i].size(2) - length) > 0:
                    mask[i].narrow(2, length, mask[i].size(2) - length).fill_(1)
            x = x.masked_fill(mask, 0)
        return x, lengths


class BatchRNN(nn.Module):
    def __init__(
        self,
        input_size,
        hidden_size,
        rnn_type=nn.LSTM,
        bidirectional=False,
        batch_norm=True,
    ):
        super(BatchRNN, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.bidirectional = bidirectional
        self.batch_norm = (
            SequenceWise(nn.BatchNorm1d(input_size)) if batch_norm else None
        )
        self.rnn = rnn_type(
            input_size=input_size,
            hidden_size=hidden_size,
            bidirectional=bidirectional,
            bias=True,
        )
        self.num_directions = 2 if bidirectional else 1

    def flatten_parameters(self):
        self.rnn.flatten_parameters()

    def forward(self, x, output_lengths, h=None):
        if self.batch_norm is not None:
            x = self.batch_norm(x)
        x = nn.utils.rnn.pack_padded_sequence(x, output_lengths)
        x, h = self.rnn(x, h)
        x, _ = nn.utils.rnn.pad_packed_sequence(x)
        if self.bidirectional:
            x = (
                x.view(x.size(0), x.size(1), 2, -1)
                .sum(2)
                .view(x.size(0), x.size(1), -1)
            )  # (TxNxH*2) -> (TxNxH) by sum
        return x, h


class Lookahead(nn.Module):
    # Wang et al 2016 - Lookahead Convolution Layer for Unidirectional Recurrent Neural Networks
    # input shape - sequence, batch, feature - TxNxH
    # output shape - same as input
    def __init__(self, n_features, context):
        super(Lookahead, self).__init__()
        assert context > 0
        self.context = context
        self.n_features = n_features
        self.pad = (0, self.context - 1)
        self.conv = nn.Conv1d(
            self.n_features,
            self.n_features,
            kernel_size=self.context,
            stride=1,
            groups=self.n_features,
            padding=0,
            bias=False,
        )

    def forward(self, x):
        x = x.transpose(0, 1).transpose(1, 2)
        x = F.pad(x, pad=self.pad, value=0)
        x = self.conv(x)
        x = x.transpose(1, 2).transpose(0, 1).contiguous()
        return x

    def __repr__(self):
        return (
            self.__class__.__name__
            + "("
            + "n_features="
            + str(self.n_features)
            + ", context="
            + str(self.context)
            + ")"
        )


class DeepSpeech(nn.Module):
    def __init__(
        self,
        n_tokens: int,
        hidden_size: int,
        hidden_layers: int,
        lookahead_context,
        pad_id=0,
    ):
        super().__init__()
        self.bidirectional = True

        self.conv = MaskConv(
            nn.Sequential(
                nn.Conv2d(1, 32, kernel_size=(41, 11), stride=(2, 2), padding=(20, 5)),
                nn.BatchNorm2d(32),
                nn.Hardtanh(0, 20, inplace=True),
                nn.Conv2d(32, 32, kernel_size=(21, 11), stride=(2, 1), padding=(10, 5)),
                nn.BatchNorm2d(32),
                nn.Hardtanh(0, 20, inplace=True),
            )
        )
        # Based on above convolutions and spectrogram size using conv formula (W - F + 2P)/ S+1
        rnn_input_size = 1024

        self.rnns = nn.Sequential(
            BatchRNN(
                input_size=rnn_input_size,
                hidden_size=hidden_size,
                rnn_type=nn.LSTM,
                bidirectional=self.bidirectional,
                batch_norm=False,
            ),
            *(
                BatchRNN(
                    input_size=hidden_size,
                    hidden_size=hidden_size,
                    rnn_type=nn.LSTM,
                    bidirectional=self.bidirectional,
                )
                for x in range(hidden_layers - 1)
            )
        )

        self.lookahead = (
            nn.Sequential(
                # consider adding batch norm?
                Lookahead(hidden_size, context=lookahead_context),
                nn.Hardtanh(0, 20, inplace=True),
            )
            if not self.bidirectional
            else None
        )

        fully_connected = nn.Sequential(
            nn.BatchNorm1d(hidden_size), nn.Linear(hidden_size, n_tokens, bias=False)
        )
        self.fc = nn.Sequential(
            SequenceWise(fully_connected),
        )

    def forward(self, spectrogram, spectrogram_length, hs=None, **batch):
        lengths = spectrogram_length.cpu().int()
        output_lengths = self.get_seq_lens(lengths)
        x, _ = self.conv(spectrogram.unsqueeze(1), output_lengths)

        sizes = x.size()
        x = x.view(
            sizes[0], sizes[1] * sizes[2], sizes[3]
        )  # Collapse feature dimension
        x = x.transpose(1, 2).transpose(0, 1).contiguous()  # TxNxH

        # if hs is None, create a list of None values corresponding to the number of rnn layers
        if hs is None:
            hs = [None] * len(self.rnns)

        new_hs = []
        for i, rnn in enumerate(self.rnns):
            x, h = rnn(x, output_lengths, hs[i])
            new_hs.append(h)

        if not self.bidirectional:  # no need for lookahead layer in bidirectional
            x = self.lookahead(x)

        x = self.fc(x)
        x = x.transpose(0, 1)
        return {
            "logits": x,
            "log_probs": F.log_softmax(x, dim=-1),
            "log_probs_length": output_lengths,
        }

    def get_seq_lens(self, input_length):
        """
        Given a 1D Tensor or Variable containing integer sequence lengths, return a 1D tensor or variable
        containing the size sequences that will be output by the network.
        :param input_length: 1D Tensor
        :return: 1D Tensor scaled by model
        """
        seq_len = input_length
        for m in self.conv.modules():
            if type(m) is nn.modules.conv.Conv2d:
                seq_len = (
                    seq_len
                    + 2 * m.padding[1]
                    - m.dilation[1] * (m.kernel_size[1] - 1)
                    - 1
                ) // m.stride[1] + 1
        return seq_len.int()
