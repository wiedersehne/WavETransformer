from abc import ABC
import torch
import pytorch_lightning as pl
import numpy as np
import ptwt
import pywt
from torch import nn
from WaveLSTM.modules.WaveConvLSTM import WaveletConv1dLSTM

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class Encoder(pl.LightningModule, ABC):
    r"""
    
    """

    def __init__(self,
                 seq_length,
                 channels,
                 pooled_width,
                 J,
                 hidden_size=256,
                 layers=1,
                 proj_size=0,
                 scale_embed_dim=128,
                 kernel_size=7,
                 wavelet="haar",
                 recursion_limit=None,   # J
                 dropout_input=0,
                 dropout_hidden=0,
                 dropout_proj=0
                 ):

        super().__init__()
        self.save_hyperparameters()
        self.wavelet = pywt.Wavelet(wavelet)
        self.seq_length = seq_length
        self.channels = channels
        self.masked_width = pooled_width
        self.J = J

        self.real_hidden_channels = proj_size if proj_size > 0 else hidden_channels
        self.hidden_channels = hidden_size
        self.layers = layers

        # recurrent network
        self.wave_rnn = WaveletConv1dLSTM(input_channels=channels,
                                          hidden_channels=hidden_size,
                                          J=self.J,
                                          layers=layers,
                                          proj_size=proj_size,
                                          kernel_size=kernel_size,
                                          dropout=dropout_input,
                                          resolution_embed_size=scale_embed_dim,
                                          )

    def __str__(self):
        s = ''
        s += f'\nData'
        s += f'\n\t Data size (?, c={self.wave_rnn.C}, h={self.wave_rnn.H}, w={self.wave_rnn.W})'
        s += f'\nRecurrent network'
        s += f'\n\t Wavelet "{self.wavelet.name}", which has decomposition length {self.wavelet.dec_len}'
        s += f"\n\t J={self.J}"
        s += f"\n\t Maximum resolution {1 / (self.wavelet.dec_len ** (self.J - 1))} " \
             f"(as a fraction of each channel's width)"
        s += str(self.wave_rnn)
        return s

    def forward(self, masked_inputs: torch.tensor, meta_data: dict):
        """
        x,                 features = [B, Strands, Chromosomes, Sequence Length]
        """
        assert len(masked_inputs) == self.J
        assert np.all([xj.shape[1] == self.channels for xj in masked_inputs])
        assert np.all([xj.shape[2] == self.masked_width for xj in masked_inputs])

        # Initialise hidden and cell states
        hidden_state = self.init_states(masked_inputs[0].size(0))

        # Loop over multiscales
        hidden_embedding = []
        for j in range(self.J):
            xj = masked_inputs[j]
            scale_embedding, hidden_state = self.wave_rnn(xj, hidden_state, j)
            hidden_embedding.append(scale_embedding)

        return hidden_embedding, meta_data

    def init_states(self, batch_size):
        """
        Initial hidden and cell tensor states. Initialised separately for each layer.
        """
        return (torch.zeros((self.layers,
                             batch_size,
                             self.real_hidden_channels,
                             self.masked_width), device=device),
                torch.zeros((self.layers,
                             batch_size,
                             self.hidden_channels,
                             self.masked_width), device=device))

