# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Testes Unitários e Integrados do Método 2 (Modulação Acústica FSK e CRC-8).
"""

import sys
import os
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.deteccao_erros import (
    calcular_crc8,
    montar_pacote_metodo2,
    desmontar_pacote_metodo2,
    codificar_mensagem_metodo2,
    decodificar_bits_metodo2,
    injetar_erro_de_bit,
)
from src.metodo2_fsk.transmissor import (
    sintetizar_bits_fsk,
    calcular_taxa_bps,
    FREQ_BIT_0,
    FREQ_BIT_1,
    DURACAO_SIMBOLO,
)
from src.metodo2_fsk.receptor import (
    decodificar_audio_fsk,
    demodular_janela_fsk,
)


class TestMetodo2(unittest.TestCase):

    def test_01_crc8_vetor_padrao_internacional(self):
        """Valida o cálculo do CRC-8 com o vetor internacional de teste '123456789' -> 0xF4."""
        dados_teste = b"123456789"
        crc = calcular_crc8(dados_teste)
        self.assertEqual(crc, 0xF4, "O CRC-8 do vetor padrão deve ser exatamente 0xF4.")

    def test_02_pacote_metodo2_integro_e_corrompido(self):
        """Valida que pacote íntegro retorna SUCESSO e pacote adulterado retorna FALHA."""
        payload = b"TESTE"
        pacote = montar_pacote_metodo2(payload)
        
        sucesso, dados, c_calc, c_rec, status = desmontar_pacote_metodo2(pacote)
        self.assertTrue(sucesso)
        self.assertEqual(dados, payload)
        self.assertIn("SUCESSO", status)

        # Adulteração de 1 byte no payload
        pacote_corrompido = bytearray(pacote)
        pacote_corrompido[2] ^= 0x01
        
        sucesso_erro, _, _, _, status_erro = desmontar_pacote_metodo2(bytes(pacote_corrompido))
        self.assertFalse(sucesso_erro)
        self.assertIn("FALHA DE TRANSMISSÃO", status_erro)

    def test_03_injecao_proposital_de_erro_fsk(self):
        """Testa a inversão proposital de 1 bit no fluxo binário do Método 2."""
        msg = "REDE"
        bits_tx = codificar_mensagem_metodo2(msg)
        
        # Inverte um bit arbitrário
        bits_com_erro = injetar_erro_de_bit(bits_tx, indice=8)
        self.assertNotEqual(bits_tx, bits_com_erro)
        
        relatorio = decodificar_bits_metodo2(bits_com_erro)
        self.assertFalse(relatorio["sucesso"])
        self.assertIn("FALHA DE TRANSMISSÃO", relatorio["status"])

    def test_04_demodulacao_janela_individual_fsk(self):
        """Testa se a detecção espectral identifica corretamente 1200 Hz (0) e 2200 Hz (1)."""
        sample_rate = 44100
        n_amostras = int(sample_rate * DURACAO_SIMBOLO)
        t = np.arange(n_amostras, dtype=np.float32) / sample_rate

        # Tom de 1200 Hz (Bit 0)
        onda_0 = np.sin(2 * np.pi * FREQ_BIT_0 * t)
        bit_0, e0, e1 = demodular_janela_fsk(onda_0, sample_rate=sample_rate)
        self.assertEqual(bit_0, 0)
        self.assertGreater(e0, e1)

        # Tom de 2200 Hz (Bit 1)
        onda_1 = np.sin(2 * np.pi * FREQ_BIT_1 * t)
        bit_1, e0, e1 = demodular_janela_fsk(onda_1, sample_rate=sample_rate)
        self.assertEqual(bit_1, 1)
        self.assertGreater(e1, e0)

    def test_05_transmissao_acustica_fsk_sem_ruido(self):
        """Testa canal acústico FSK de ponta a ponta sem ruído."""
        msg = "OK"
        bits_tx = codificar_mensagem_metodo2(msg)
        audio = sintetizar_bits_fsk(bits_tx)
        
        bits_rx = decodificar_audio_fsk(audio, quantidade_bits=len(bits_tx))
        relatorio = decodificar_bits_metodo2(bits_rx)
        
        self.assertTrue(relatorio["sucesso"])
        self.assertEqual(relatorio["mensagem"], msg)

    def test_06_transmissao_acustica_fsk_com_ruido(self):
        """Testa canal acústico FSK com adição de ruído gaussiano."""
        msg = "SOM"
        bits_tx = codificar_mensagem_metodo2(msg)
        audio = sintetizar_bits_fsk(bits_tx)
        
        np.random.seed(123)
        ruido = np.random.normal(0, 0.04, len(audio)).astype(np.float32)
        audio_ruidoso = audio + ruido
        
        bits_rx = decodificar_audio_fsk(audio_ruidoso, quantidade_bits=len(bits_tx))
        relatorio = decodificar_bits_metodo2(bits_rx)
        
        self.assertTrue(relatorio["sucesso"])
        self.assertEqual(relatorio["mensagem"], msg)

    def test_07_calculo_taxa_bps(self):
        """Verifica o cálculo de taxa de transferência em bps."""
        taxas = calcular_taxa_bps(num_bits_dados=32, num_bits_totais=48)
        self.assertEqual(taxas["taxa_teorica_bps"], 40.0)
        self.assertGreater(taxas["taxa_pratica_bps"], 15.0)

    def test_08_demodulacao_autonoma_sem_tamanho_previo(self):
        """Testa recepção cega FSK (com silêncio inicial e final) sem passar quantidade_bits."""
        msg = "OI"
        bits_tx = codificar_mensagem_metodo2(msg)
        audio = sintetizar_bits_fsk(bits_tx)
        
        # Insere silêncio antes e depois (simulando gravação de microfone)
        sinal_com_silencio = np.concatenate([
            np.zeros(10000, dtype=np.float32),
            audio,
            np.zeros(15000, dtype=np.float32)
        ])
        
        bits_rx = decodificar_audio_fsk(sinal_com_silencio, quantidade_bits=None)
        relatorio = decodificar_bits_metodo2(bits_rx)
        self.assertTrue(relatorio["sucesso"], "Receptor FSK deve decodificar autonomamente sem conhecimento prévio do tamanho.")
        self.assertEqual(relatorio["mensagem"], msg)

    def test_09_fluxo_metodo2_com_entrada_manual_de_impactos(self):
        """
        Valida o Requisito 3 da correção:
        Usuário bate no microfone -> bits -> codificador FSK -> alto-falante -> receptor FSK -> CRC -> mensagem.
        """
        from src.conversao import bits_para_bytes, bytes_para_bits
        from src.metodo1_batidas.transmissor import sintetizar_bits_metodo1
        from src.metodo1_batidas.receptor import decodificar_audio_metodo1
        
        # 1. Usuário bate os bits da palavra 'OI' em ASCII
        # 'O' = 01001111, 'I' = 01001001
        bits_palavra = [0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1]
        
        # Simula som das batidas físicas do usuário
        audio_batidas = sintetizar_bits_metodo1(bits_palavra, sample_rate=44100, tempo_bit=0.6)
        
        # 2. Detector de impactos captura os bits
        bits_detectados, _ = decodificar_audio_metodo1(audio_batidas, sample_rate=44100)
        self.assertEqual(bits_detectados, bits_palavra)
        
        # 3. Bits são convertidos em pacote FSK com CRC-8
        dados_bytes = bits_para_bytes(bits_detectados)
        pacote_fsk = montar_pacote_metodo2(dados_bytes)
        bits_fsk = bytes_para_bits(pacote_fsk)
        
        # 4. Modulação FSK e transmissão acústica
        audio_fsk = sintetizar_bits_fsk(bits_fsk)
        
        # 5. Receptor FSK demodula o áudio e valida integridade via CRC-8
        bits_rx = decodificar_audio_fsk(audio_fsk)
        relatorio = decodificar_bits_metodo2(bits_rx)
        
        self.assertTrue(relatorio["sucesso"])
        self.assertEqual(relatorio["mensagem"], "OI")
        self.assertEqual(relatorio["payload_bytes"], b"OI")

    def test_10_rejeicao_de_ruido_puro(self):
        """Verifica que sinal contendo apenas ruído gaussiano não aciona falsamente o preâmbulo FSK."""
        from src.metodo2_fsk.receptor import detectar_preambulo
        np.random.seed(999)
        ruido = np.random.normal(0, 0.05, 44100).astype(np.float32)
        inicio = detectar_preambulo(ruido)
        self.assertIsNone(inicio, "Ruído puro não deve acionar falso-positivo de preâmbulo FSK.")

    def test_11_demodulacao_com_longo_atraso_e_ruido(self):
        """
        Simula o cenário físico real: receptor começa a escutar 2.5 segundos antes
        de o transmissor começar, em ambiente com ruído acústico de fundo.
        """
        msg = "OI"
        bits_tx = codificar_mensagem_metodo2(msg)
        audio_tx = sintetizar_bits_fsk(bits_tx)

        # 2.5 segundos de ruído ambiente antes + sinal com ruído + 1.5 segundos de ruído depois
        np.random.seed(42)
        sample_rate = 44100
        ruido_antes = np.random.normal(0, 0.02, int(sample_rate * 2.5)).astype(np.float32)
        ruido_depois = np.random.normal(0, 0.02, int(sample_rate * 1.5)).astype(np.float32)
        ruido_sinal = np.random.normal(0, 0.02, len(audio_tx)).astype(np.float32)

        sinal_completo = np.concatenate([
            ruido_antes,
            audio_tx + ruido_sinal,
            ruido_depois
        ])

        bits_rx, diag = decodificar_audio_fsk(sinal_completo, quantidade_bits=None, retornar_diagnostico=True)
        relatorio = decodificar_bits_metodo2(bits_rx)

        self.assertTrue(relatorio["sucesso"], f"Receptor deve sincronizar e validar CRC mesmo com 2.5s de atraso inicial. Status: {relatorio['status']}")
        self.assertEqual(relatorio["mensagem"], msg)
        self.assertGreater(diag["confianca_media"], 80.0)


if __name__ == "__main__":
    unittest.main()

