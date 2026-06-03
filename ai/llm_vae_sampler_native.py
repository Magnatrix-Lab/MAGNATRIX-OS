"""VAE Sampler - Variational autoencoder sampling for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple
import random
import math

@dataclass
class VAESampler:
    latent_dim: int = 2
    mu_net: List[List[float]] = field(default_factory=list)
    logvar_net: List[List[float]] = field(default_factory=list)
    decode_net: List[List[float]] = field(default_factory=list)

    def __post_init__(self):
        if not self.mu_net:
            for dim in [latent_dim, latent_dim]:
                setattr(self, ['mu_net','logvar_net','decode_net'][len([self.mu_net,self.logvar_net,self.decode_net])], [[random.gauss(0,0.1) for _ in range(dim)] for _ in range(dim)])

    def encode(self, x: List[float]) -> Tuple[List[float], List[float]]:
        mu = [sum(x[j]*self.mu_net[i][j] for j in range(len(x))) for i in range(self.latent_dim)]
        logvar = [sum(x[j]*self.logvar_net[i][j] for j in range(len(x))) for i in range(self.latent_dim)]
        return mu, logvar

    def sample(self, mu: List[float], logvar: List[float]) -> List[float]:
        return [mu[i] + math.exp(0.5*logvar[i])*random.gauss(0,1) for i in range(self.latent_dim)]

    def decode(self, z: List[float]) -> List[float]:
        return [sum(z[j]*self.decode_net[i][j] for j in range(self.latent_dim)) for i in range(self.latent_dim)]

    def forward(self, x: List[float]) -> Tuple[List[float], List[float], List[float]]:
        mu, logvar = self.encode(x)
        z = self.sample(mu, logvar)
        recon = self.decode(z)
        return recon, mu, logvar

    def stats(self) -> dict:
        return {"latent_dim": self.latent_dim}

def run():
    vae = VAESampler(2)
    x = [1.0, 0.5]
    recon, mu, logvar = vae.forward(x)
    print("Recon:", [round(v,4) for v in recon])
    print("Stats:", vae.stats())

if __name__ == "__main__": run()
