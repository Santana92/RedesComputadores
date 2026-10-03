# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Módulo do Método 2: Transmissão por Duração do Impacto Acústico e CRC-8.

Exporta os componentes do Transmissor e do Receptor.
"""

from .transmissor import (
    FREQ_IMPACTO,
    DURACAO_IMPACTO_CURTO,
    DURACAO_IMPACTO_LONGO,
    LIMIAR_DURACAO,
    INTERVALO_ENTRE_IMPACTOS,
    SILENCIO_GUARDA,
    PADRAO_PREAMBULO,
    gerar_som_impacto_duracao,
    sintetizar_bits_duracao,
    transmitir_audio_duracao,
    parar_transmissao_duracao,
    calcular_taxa_bps,
)

from .receptor import (
    calcular_envelope_energia,
    detectar_impactos_com_duracao,
    localizar_preambulo,
    demodular_bits_duracao,
    decodificar_audio_duracao,
    gravar_audio_microfone_duracao,
)

__all__ = [
    "FREQ_IMPACTO",
    "DURACAO_IMPACTO_CURTO",
    "DURACAO_IMPACTO_LONGO",
    "LIMIAR_DURACAO",
    "INTERVALO_ENTRE_IMPACTOS",
    "SILENCIO_GUARDA",
    "PADRAO_PREAMBULO",
    "gerar_som_impacto_duracao",
    "sintetizar_bits_duracao",
    "transmitir_audio_duracao",
    "parar_transmissao_duracao",
    "calcular_taxa_bps",
    "calcular_envelope_energia",
    "detectar_impactos_com_duracao",
    "localizar_preambulo",
    "demodular_bits_duracao",
    "decodificar_audio_duracao",
    "gravar_audio_microfone_duracao",
]
