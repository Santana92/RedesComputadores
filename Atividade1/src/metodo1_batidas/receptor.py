# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Receptor do Método 1 (Quantidade de Impactos).

Responsável por capturar o áudio do microfone em tempo real e processar
os impactos sonoros tanto em:
1. TRANSMISSÃO AUTOMÁTICA: impactos gerados pelo computador e emitidos pelo alto-falante.
2. TRANSMISSÃO MANUAL: impactos produzidos fisicamente pelo usuário (palmas, batidas
   na mesa, estalos de dedos, cliques de caneta) captados diretamente pelo microfone.

Em ambas as modalidades, a regra de interpretação é idêntica:
- 1 batida isolada = BIT 0 (•)
- 2 batidas consecutivas rápidas = BIT 1 (••)

O receptor rejeita reverberações através de debounce adaptativo e monta
quadros de 9 bits (8 bits de dados + 1 bit de paridade par).
"""

import time
from typing import List, Tuple, Callable, Optional, Dict, Any
import numpy as np
import sounddevice as sd


# ==============================================================================
# DETECTOR DE BATIDAS EM TEMPO REAL (STREAM DO MICROFONE)
# ==============================================================================

class DetectorBatidasTempoReal:
    """
    Detector contínuo de impactos acústicos em tempo real.
    
    Funciona tanto para a Transmissão Automática (alto-falante) quanto
    para a Transmissão Manual (palmas, batidas na mesa, caneta, estalos).
    
    Recebe fluxo de áudio contínuo do microfone e emprega uma máquina de estados:
    - IDLE: Monitora o áudio aguardando amplitude superar o limiar.
    - WAITING_SECOND_TAP: Primeira batida detectada. Aguarda janela temporal (janela_dupla_s)
      para verificar se ocorre uma 2ª batida consecutiva rápida.
      * Se uma 2ª batida ocorrer (após debounce): emite BIT 1 (••).
      * Se o tempo expirar sem 2ª batida: emite BIT 0 (•).
    """

    def __init__(
        self,
        callback_bit: Callable[[int, str], None],
        callback_evento: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        limiar: float = 0.08,
        debounce_s: float = 0.085,
        janela_dupla_s: float = 0.36,
        sample_rate: int = 44100,
        tamanho_bloco: int = 512
    ):
        self.callback_bit = callback_bit
        self.callback_evento = callback_evento
        self.limiar = limiar
        self.debounce_s = debounce_s
        self.janela_dupla_s = janela_dupla_s
        self.sample_rate = sample_rate
        self.tamanho_bloco = tamanho_bloco

        # Estado da Máquina
        self.estado = "IDLE"  # 'IDLE' ou 'WAITING_SECOND_TAP'
        self.tempo_primeira_batida = 0.0
        self.tempo_refratario_ate = 0.0
        self.stream: Optional[sd.InputStream] = None
        self.ativo = False

    def iniciar(self) -> None:
        """Inicia a captura contínua do microfone."""
        if self.ativo:
            return
        self.reiniciar_estado()
        self.stream = sd.InputStream(
            callback=self._audio_callback,
            channels=1,
            samplerate=self.sample_rate,
            blocksize=self.tamanho_bloco,
            dtype=np.float32
        )
        self.stream.start()
        self.ativo = True
        if self.callback_evento:
            self.callback_evento("MICROFONE_INICIADO", {"limiar": self.limiar})

    def parar(self) -> None:
        """Interrompe a escuta do microfone."""
        self.ativo = False
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        self.reiniciar_estado()
        if self.callback_evento:
            self.callback_evento("MICROFONE_PARADO", {})

    def reiniciar_estado(self) -> None:
        """Reseta as variáveis temporais da máquina de detecção."""
        self.estado = "IDLE"
        self.tempo_primeira_batida = 0.0
        self.tempo_refratario_ate = 0.0

    def definir_limiar(self, novo_limiar: float) -> None:
        """Ajusta o limiar de sensibilidade de pico."""
        self.limiar = max(0.01, float(novo_limiar))

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        """Callback invocado pelo driver de áudio a cada ~11.6 ms."""
        if not self.ativo:
            return

        agora = time.time()
        # Removemos o offset DC (média do sinal) para centralizar a onda em zero antes de medir o pico
        sinal = indata[:, 0]
        sinal = sinal - np.mean(sinal)
        pico = float(np.max(np.abs(sinal))) if len(sinal) > 0 else 0.0

        # Notifica medidor de volume para a interface (feedback visual de atividade)
        if self.callback_evento and agora % 0.05 < 0.015:
            self.callback_evento("NIVEL_AUDIO", {"pico": pico, "limiar": self.limiar})

        # ----------------------------------------------------------------------
        # MÁQUINA DE ESTADOS DA DETECÇÃO DE BATIDAS:
        # Fizemos essa lógica temporal com debounce de 85 ms e janela de 350 ms.
        # ----------------------------------------------------------------------
        if self.estado == "WAITING_SECOND_TAP":
            delta = agora - self.tempo_primeira_batida

            # Se a janela de 350 ms expirou sem uma 2ª batida, confirmamos que foi 1 batida isolada = Bit 0
            if delta > self.janela_dupla_s:
                self.callback_bit(0, "1 impacto isolado (•)")
                self.tempo_refratario_ate = agora + 0.05
                self.estado = "IDLE"
                if self.callback_evento:
                    self.callback_evento("BIT_EMITIDO", {"bit": 0, "descricao": "1 impacto isolado (•)", "simbolo": "•"})

            # Se uma 2ª batida ocorreu após o debounce (85 ms) e antes de expirar a janela, é Bit 1
            elif delta >= self.debounce_s and pico > self.limiar:
                self.callback_bit(1, "2 impactos consecutivos rápidos (••)")
                # Aplicamos debounce refratário para não captar o eco da 2ª batida
                self.tempo_refratario_ate = agora + self.debounce_s
                self.estado = "IDLE"
                if self.callback_evento:
                    self.callback_evento("BIT_EMITIDO", {"bit": 1, "descricao": "2 impactos consecutivos rápidos (••)", "simbolo": "••"})

        elif self.estado == "IDLE":
            # Aguardamos passar o período de debounce de qualquer evento anterior
            if agora >= self.tempo_refratario_ate:
                if pico > self.limiar:
                    # Primeira batida registrada! Guardamos o instante e aguardamos até 350 ms por outra
                    self.tempo_primeira_batida = agora
                    self.estado = "WAITING_SECOND_TAP"
                    if self.callback_evento:
                        self.callback_evento("PRIMEIRA_BATIDA", {
                            "texto": "Impacto detectado! Aguardando 2ª batida...",
                            "pico": pico
                        })
                elif pico > self.limiar * 0.45:
                    # Som presente mas abaixo do limiar (aviso didático ao usuário)
                    if self.callback_evento:
                        self.callback_evento("SOM_FRACO", {
                            "texto": "⚠ Som muito fraco para registro",
                            "pico": pico,
                            "limiar": self.limiar
                        })

    def calibrar_ruido(self, duracao_s: float = 1.5) -> Tuple[float, float]:
        """
        Mede o ruído de fundo da sala por duracao_s segundos e define
        automaticamente um limiar adaptativo ótimo.
        Retorna (ruido_medido, novo_limiar).
        """
        was_active = self.ativo
        if was_active:
            self.parar()

        # Gravamos 1.5s de silêncio na sala para calcular o percentil 95 do ruído de fundo
        amostras_totais = int(self.sample_rate * duracao_s)
        gravacao = sd.rec(amostras_totais, samplerate=self.sample_rate, channels=1, dtype=np.float32)
        sd.wait()

        sinal = gravacao[:, 0]
        sinal = sinal - np.mean(sinal)
        ruido_pico = float(np.percentile(np.abs(sinal), 95))

        # Foi escolhida essa margem (2.8x o ruído + offset) para o limiar ficar acima do ruído da sala
        novo_limiar = max(0.04, min(0.40, ruido_pico * 2.8 + 0.03))
        self.definir_limiar(novo_limiar)

        if was_active:
            self.iniciar()

        return ruido_pico, novo_limiar


# ==============================================================================
# FUNÇÕES DE PROCESSAMENTO EM LOTE (OFFLINE / TESTES UNITÁRIOS)
# ==============================================================================

def calcular_envelope_energia(
    sinal: np.ndarray,
    tamanho_janela_ms: float = 12.0,
    sample_rate: int = 44100
) -> np.ndarray:
    """Calcula o envelope de amplitude suave do sinal de áudio."""
    sinal_centralizado = sinal - np.mean(sinal)
    retificado = np.abs(sinal_centralizado)
    janela_amostras = max(1, int(sample_rate * (tamanho_janela_ms / 1000.0)))
    filtro = np.ones(janela_amostras, dtype=np.float32) / float(janela_amostras)
    return np.convolve(retificado, filtro, mode="same")


def detectar_instantes_batidas(
    sinal: np.ndarray,
    sample_rate: int = 44100,
    sensibilidade: float = 0.30,
    debounce_ms: float = 90.0
) -> List[float]:
    """Detecta os instantes exatos de tempo em que ocorreram batidas."""
    if len(sinal) == 0:
        return []
    
    envelope = calcular_envelope_energia(sinal, sample_rate=sample_rate)
    pico_maximo = float(np.max(envelope))
    ruido_fundo = float(np.percentile(envelope, 30))
    
    if pico_maximo < 0.02:
        return []
    
    limiar = max(0.04, ruido_fundo * 3.5, ruido_fundo + (pico_maximo - ruido_fundo) * sensibilidade)
    debounce_amostras = int(sample_rate * (debounce_ms / 1000.0))
    instantes = []
    
    i = 0
    total_amostras = len(envelope)
    while i < total_amostras:
        if envelope[i] > limiar:
            janela_fim = min(total_amostras, i + debounce_amostras)
            pos_pico_local = i + int(np.argmax(envelope[i:janela_fim]))
            instantes.append(float(pos_pico_local / sample_rate))
            i = janela_fim
        else:
            i += 1
            
    return instantes


def classificar_batidas_em_bits(
    instantes_batidas: List[float],
    limiar_consecutivo: float = 0.35
) -> List[int]:
    """
    Converte a sequência temporal de instantes de impactos em bits:
    - 2 impactos consecutivos rápidos (intervalo <= limiar_consecutivo) = BIT 1 (••)
    - 1 impacto isolado (intervalo > limiar_consecutivo) = BIT 0 (•)

    Aplica-se tanto a impactos gerados pelo alto-falante quanto a impactos
    físicos manuais (palmas, batidas na mesa, estalos de dedos, batidas com caneta).
    """
    bits = []
    i = 0
    total = len(instantes_batidas)
    while i < total:
        if i + 1 < total:
            intervalo = instantes_batidas[i + 1] - instantes_batidas[i]
            if intervalo <= limiar_consecutivo:
                bits.append(1)
                i += 2
                continue
        bits.append(0)
        i += 1
    return bits


def decodificar_audio_metodo1(
    sinal: np.ndarray,
    sample_rate: int = 44100
) -> Tuple[List[int], List[float]]:
    """Processa o áudio gravado e retorna bits recuperados e instantes."""
    instantes = detectar_instantes_batidas(sinal, sample_rate=sample_rate)
    bits = classificar_batidas_em_bits(instantes)
    return bits, instantes


def gravar_audio_microfone(
    duracao_segundos: float,
    sample_rate: int = 44100
) -> np.ndarray:
    """Grava áudio do microfone por uma duração fixa."""
    gravacao = sd.rec(int(duracao_segundos * sample_rate), samplerate=sample_rate, channels=1, dtype=np.float32)
    sd.wait()
    return gravacao.flatten()
