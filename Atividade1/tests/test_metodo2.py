# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Testes Unitários e Integrados do Método 2 (Duração do Impacto e CRC-8).

Cobre:
1. Cálculo de CRC-8 padrão ATM (0x07) e vetor de teste internacional.
2. Formação e validação de pacotes com cabeçalho de comprimento e CRC-8.
3. Inversão proposital de bits para comprovação de detecção de erro.
4. Classificação individual de impactos curtos (0) e longos (1) por limiar.
5. Transmissão e recepção acústica simulada (sem ruído e com ruído).
6. Sincronização via preâmbulo (10101010) e extração autônoma.
7. Cálculo de taxas de transmissão teórica e prática.
8. Mensagens maiores e validação ponta a ponta.
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
from src.metodo2_duracao.transmissor import (
    sintetizar_bits_duracao,
    calcular_taxa_bps,
    gerar_som_impacto_duracao,
    DURACAO_IMPACTO_CURTO,
    DURACAO_IMPACTO_LONGO,
    LIMIAR_DURACAO,
    PADRAO_PREAMBULO,
)
from src.metodo2_duracao.receptor import (
    decodificar_audio_duracao,
    detectar_impactos_com_duracao,
    localizar_preambulo,
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

    def test_03_injecao_proposital_de_erro_crc8(self):
        """Testa a inversão proposital de 1 bit no fluxo binário do Método 2."""
        msg = "REDE"
        bits_tx = codificar_mensagem_metodo2(msg)

        # Inverte um bit arbitrário
        bits_com_erro = injetar_erro_de_bit(bits_tx, indice=8)
        self.assertNotEqual(bits_tx, bits_com_erro)

        relatorio = decodificar_bits_metodo2(bits_com_erro)
        self.assertFalse(relatorio["sucesso"])
        self.assertIn("FALHA DE TRANSMISSÃO", relatorio["status"])

    def test_04_classificacao_impacto_curto_e_longo(self):
        """Testa se a detecção de envelope diferencia corretamente 50 ms (0) e 160 ms (1)."""
        sample_rate = 44100

        # Pulso curto de 50 ms (Bit 0)
        silencio_padrao = np.zeros(int(sample_rate * 0.1), dtype=np.float32)
        onda_0 = np.concatenate([silencio_padrao, gerar_som_impacto_duracao(DURACAO_IMPACTO_CURTO, sample_rate), silencio_padrao])
        bits_0, rel_0 = detectar_impactos_com_duracao(onda_0, sample_rate=sample_rate)
        self.assertEqual(len(bits_0), 1)
        self.assertEqual(bits_0[0], 0)
        self.assertEqual(rel_0[0]["classificacao"], "CURTO")
        self.assertLess(rel_0[0]["duracao_ms"], LIMIAR_DURACAO * 1000.0)

        # Pulso longo de 160 ms (Bit 1)
        onda_1 = np.concatenate([silencio_padrao, gerar_som_impacto_duracao(DURACAO_IMPACTO_LONGO, sample_rate), silencio_padrao])
        bits_1, rel_1 = detectar_impactos_com_duracao(onda_1, sample_rate=sample_rate)
        self.assertEqual(len(bits_1), 1)
        self.assertEqual(bits_1[0], 1)
        self.assertEqual(rel_1[0]["classificacao"], "LONGO")
        self.assertGreaterEqual(rel_1[0]["duracao_ms"], LIMIAR_DURACAO * 1000.0)

    def test_05_transmissao_acustica_duracao_sem_ruido(self):
        """Testa canal acústico por duração de ponta a ponta sem ruído."""
        msg = "OK"
        bits_tx = codificar_mensagem_metodo2(msg)
        audio = sintetizar_bits_duracao(bits_tx, incluir_preambulo=True)

        bits_rx = decodificar_audio_duracao(audio, quantidade_bits=len(bits_tx))
        relatorio = decodificar_bits_metodo2(bits_rx)

        self.assertTrue(relatorio["sucesso"])
        self.assertEqual(relatorio["mensagem"], msg)

    def test_06_transmissao_acustica_duracao_com_ruido(self):
        """Testa canal acústico por duração com adição de ruído gaussiano."""
        msg = "SOM"
        bits_tx = codificar_mensagem_metodo2(msg)
        audio = sintetizar_bits_duracao(bits_tx, incluir_preambulo=True)

        np.random.seed(123)
        ruido = np.random.normal(0, 0.03, len(audio)).astype(np.float32)
        audio_ruidoso = audio + ruido

        bits_rx = decodificar_audio_duracao(audio_ruidoso, quantidade_bits=len(bits_tx))
        relatorio = decodificar_bits_metodo2(bits_rx)

        self.assertTrue(relatorio["sucesso"])
        self.assertEqual(relatorio["mensagem"], msg)

    def test_07_calculo_taxa_bps(self):
        """Verifica o cálculo de taxa de transferência em bps baseado na duração."""
        taxas = calcular_taxa_bps(num_bits_dados=32, num_bits_totais=48, incluir_preambulo=True)
        self.assertGreater(taxas["taxa_teorica_bps"], 3.0)
        self.assertLess(taxas["taxa_teorica_bps"], 6.0)
        self.assertGreater(taxas["taxa_pratica_bps"], 1.5)

    def test_08_demodulacao_autonoma_sem_tamanho_previo(self):
        """Testa recepção cega (com silêncio inicial e final) sem passar quantidade_bits."""
        msg = "OI"
        bits_tx = codificar_mensagem_metodo2(msg)
        audio = sintetizar_bits_duracao(bits_tx, incluir_preambulo=True)

        # Insere silêncio antes e depois (simulando espera de gravação de microfone)
        sinal_com_silencio = np.concatenate([
            np.zeros(20000, dtype=np.float32),
            audio,
            np.zeros(25000, dtype=np.float32)
        ])

        bits_rx = decodificar_audio_duracao(sinal_com_silencio, quantidade_bits=None)
        relatorio = decodificar_bits_metodo2(bits_rx)
        self.assertTrue(relatorio["sucesso"], "Receptor deve decodificar autonomamente sem conhecimento prévio do tamanho.")
        self.assertEqual(relatorio["mensagem"], msg)

    def test_09_mensagem_maior(self):
        """Valida a transmissão de uma mensagem maior ('REDE')."""
        msg = "REDE"
        bits_tx = codificar_mensagem_metodo2(msg)
        audio = sintetizar_bits_duracao(bits_tx, incluir_preambulo=True)

        bits_rx = decodificar_audio_duracao(audio, quantidade_bits=len(bits_tx))
        relatorio = decodificar_bits_metodo2(bits_rx)

        self.assertTrue(relatorio["sucesso"])
        self.assertEqual(relatorio["mensagem"], msg)


if __name__ == "__main__":
    unittest.main()
