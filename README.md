# Automatic Speech Recognition (ASR) with PyTorch

<p align="center">
  <a href="#about">About</a> •
  <a href="#installation">Installation</a> •
  <a href="#how-to-use">How To Use</a> •
  <a href="#credits">Credits</a> •
  <a href="#license">License</a>
</p>

## About

This repository demonstrates an attempt to solve the Automatic Speech Recognition (ASR) task using PyTorch. The model architecture is based on [Deepspeech2](https://arxiv.org/abs/1512.02595). The trained model achieved the following Character Error Rate (CER) and Word Error Rate (WER) metrics on the [Librispeech](https://www.openslr.org/12) test-clean dataset:
```
val_CER_(Argmax): 0.16772798662934774
val_WER_(Argmax): 0.4320796105808388
```
You can view the WandB charts and example predictions at this [link](https://wandb.ai/muniev-hse/hse_asr/workspace). You can read WandB report at this [link](https://wandb.ai/muniev-hse/hse_asr/reports/-2-ASR--VmlldzoxMDgzNDUyOA).
See the task assignment [here](https://github.com/NickKar30/SpeechAI/tree/main/hw2).

## Installation

Follow these steps to install the project:

0. (Optional) Create and activate new environment using [`conda`](https://conda.io/projects/conda/en/latest/user-guide/getting-started.html) or `venv` ([`+pyenv`](https://github.com/pyenv/pyenv)).

   a. `conda` version:

   ```bash
   # create env
   conda create -n project_env python=PYTHON_VERSION

   # activate env
   conda activate project_env
   ```

   b. `venv` (`+pyenv`) version:

   ```bash
   # create env
   ~/.pyenv/versions/PYTHON_VERSION/bin/python3 -m venv project_env

   # alternatively, using default python version
   python3 -m venv project_env

   # activate env
   source project_env
   ```

1. Install all required packages

   ```bash
   pip install -r requirements.txt
   ```

2. Install `pre-commit`:
   ```bash
   pre-commit install
   ```

## How To Use

### Train
To train a model, run the following command:

```bash
python3 train.py -cn=deepspeech.yaml
```
### Inference
To run inference (evaluate the model and save predictions):

1. Download trained model:
```bash
gdown 1u-jC1jnATKtfUD2EQPxYlmr0U2QBG7SP
```
2. Move the downloaded model to the directory specified in the `from_pretrained` variable in the `inference.yaml` configuration file.
3. Run the inference script:
```bash
python3 inference.py -cn=inference.yaml
```
> [!NOTE]
> The from_pretrained variable in `inference.yaml` must point to the directory containing the downloaded model.

## Credits

This repository is based on a [PyTorch Project Template](https://github.com/Blinorot/pytorch_project_template).

## License

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](/LICENSE)
