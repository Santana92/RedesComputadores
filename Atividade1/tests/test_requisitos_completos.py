# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Suíte de Testes Formais dos 9 Requisitos da Atividade.

Mapeia 1 a 1 os 9 pontos exigidos na especificação:
1. Transmissão sem ruído;
2. Transmissão com ruído;
3. Mensagem curta;
4. Mensagem maior;
5. Erro proposital em um bit;
6. Quadro correto;
7. Quadro corrompido;
8. Cálculo de paridade;
9. Detecção de erro do Método 2.
"""

import sys
import os
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.conversao import mensagem_para_bits, bits_para_mensagem
from src.deteccao_erros import (
    calcular_bit_paridade_par,
    criar_quadro_metodo1,
    verificar_quadro_metodo1,
    codificar_mensagem_metodo1,
    decodificar_quadros_metodo1,
    calcular_crc8,
    codificar_mensagem_metodo2,
    decodificar_bits_metodo2,
    injetar_erro_de_bit,
)
from src.metodo1_batidas.transmissor import sintetizar_bits_metodo1
from src.metodo1_batidas.receptor import decodificar_audio_metodo1
from src.metodo2_fsk.transmissor import sintetizar_bits_fsk
from src.metodo2_fsk.receptor import decodificar_audio_fsk


class TestRequisitosAtividade(unittest.TestCase):

    # --------------------------------------------------------------------------
    # REQUISITO 8: CÁLCULO DE PARIDADE (Exemplos oficiais)
    # --------------------------------------------------------------------------
    def test_req_08_calculo_de_paridade(self):
        """Requisito 8: Validação matemática da regra de paridade par."""
        # Se contagem de 1s for par -> b9 = 0
        self.assertEqual(calcular_bit_paridade_par([1, 1, 0, 0, 0, 0, 0, 0]), 0)
        # Se contagem de 1s for ímpar -> b9 = 1
        self.assertEqual(calcular_bit_paridade_par([1, 1, 1, 0, 0, 0, 0, 0]), 1)

    # --------------------------------------------------------------------------
    # REQUISITO 6: QUADRO CORRETO
    # --------------------------------------------------------------------------
    def test_req_06_quadro_correto(self):
        """Requisito 6: Quadro válido de 9 bits deve ser validado com SUCESSO."""
        dados = [0, 1, 0, 0, 0, 0, 0, 1]  # 'A'
        quadro = criar_quadro_metodo1(dados)
        sucesso, dados_out, p_esp, p_rec = verificar_quadro_metodo1(quadro)
        self.assertTrue(sucesso)
        self.assertEqual(p_esp, p_rec)

    # --------------------------------------------------------------------------
    # REQUISITO 7: QUADRO CORROMPIDO
    # --------------------------------------------------------------------------
    def test_req_07_quadro_corrompido(self):
        """Requisito 7: Quadro com erro deve retornar FALHA DE TRANSMISSÃO."""
        dados = [0, 1, 0, 0, 0, 0, 0, 1]
        quadro = criar_quadro_metodo1(dados)
        quadro_com_erro = list(quadro)
        quadro_com_erro[0] = 1 - quadro_com_erro[0]  # Inverte bit de dados
        
        sucesso, _, p_esp, p_rec = verificar_quadro_metodo1(quadro_com_erro)
        self.assertFalse(sucesso)
        self.assertNotEqual(p_esp, p_rec)

    # --------------------------------------------------------------------------
    # REQUISITO 5: ERRO PROPOSITAL EM UM BIT
    # --------------------------------------------------------------------------
    def test_req_05_erro_proposital_em_um_bit(self):
        """Requisito 5: Inversão determinística de 1 bit sem depender de ruído real."""
        # Método 1
        quadro = [1, 1, 0, 0, 0, 0, 0, 0, 0]
        quadro_alterado = injetar_erro_de_bit(quadro, indice=8)
        self.assertFalse(verificar_quadro_metodo1(quadro_alterado)[0])

        # Método 2
        bits_tx = codificar_mensagem_metodo2("REDE")
        bits_alterados = injetar_erro_de_bit(bits_tx, indice=10)
        relatorio = decodificar_bits_metodo2(bits_alterados)
        self.assertFalse(relatorio["sucesso"])
        self.assertIn("FALHA DE TRANSMISSÃO", relatorio["status"])

    # --------------------------------------------------------------------------
    # REQUISITO 9: DETECÇÃO DE ERRO DO MÉTODO 2 (CRC-8)
    # --------------------------------------------------------------------------
    def test_req_09_deteccao_erro_metodo2_crc8(self):
        """Requisito 9: Algoritmo CRC-8 detecta corrupção e aprova integridade."""
        # Vetor padrão de teste internacional
        self.assertEqual(calcular_crc8(b"123456789"), 0xF4)
        
        bits_tx = codificar_mensagem_metodo2("SISTEMAS")
        rel_ok = decodificar_bits_metodo2(bits_tx)
        self.assertTrue(rel_ok["sucesso"])
        self.assertIn("SUCESSO", rel_ok["status"])
        
        bits_err = injetar_erro_de_bit(bits_tx, indice=5)
        rel_err = decodificar_bits_metodo2(bits_err)
        self.assertFalse(rel_err["sucesso"])
        self.assertIn("FALHA DE TRANSMISSÃO", rel_err["status"])

    # --------------------------------------------------------------------------
    # REQUISITO 1: TRANSMISSÃO SEM RUÍDO
    # --------------------------------------------------------------------------
    def test_req_01_transmissao_sem_ruido(self):
        """Requisito 1: Canal ideal sem perturbação."""
        # Teste Método 2 FSK
        bits_tx = codificar_mensagem_metodo2("OK")
        audio = sintetizar_bits_fsk(bits_tx)
        bits_rx = decodificar_audio_fsk(audio, quantidade_bits=len(bits_tx))
        rel = decodificar_bits_metodo2(bits_rx)
        self.assertTrue(rel["sucesso"])
        self.assertEqual(rel["mensagem"], "OK")

    # --------------------------------------------------------------------------
    # REQUISITO 2: TRANSMISSÃO COM RUÍDO
    # --------------------------------------------------------------------------
    def test_req_02_transmissao_com_ruido(self):
        """Requisito 2: Canal ruidoso com ruído acústico aditivo."""
        # Teste Método 2 sob ruído
        bits_tx = codificar_mensagem_metodo2("SOM")
        audio = sintetizar_bits_fsk(bits_tx)
        ruido = np.random.normal(0, 0.04, len(audio)).astype(np.float32)
        audio_ruidoso = audio + ruido
        
        bits_rx = decodificar_audio_fsk(audio_ruidoso, quantidade_bits=len(bits_tx))
        rel = decodificar_bits_metodo2(bits_rx)
        self.assertTrue(rel["sucesso"])
        self.assertEqual(rel["mensagem"], "SOM")

    # --------------------------------------------------------------------------
    # REQUISITO 3: MENSAGEM CURTA
    # --------------------------------------------------------------------------
    def test_req_03_mensagem_curta(self):
        """Requisito 3: Transmissão de mensagem curta (ex.: 'A')."""
        msg = "A"
        # Método 1
        bits_tx_m1 = codificar_mensagem_metodo1(mensagem_para_bits(msg))
        self.assertEqual(len(bits_tx_m1), 9)  # 1 caractere = 1 quadro de 9 bits
        suc_m1, dados_m1, _ = decodificar_quadros_metodo1(bits_tx_m1)
        self.assertTrue(suc_m1)
        self.assertEqual(bits_para_mensagem(dados_m1), msg)

        # Método 2
        bits_tx_m2 = codificar_mensagem_metodo2(msg)
        rel_m2 = decodificar_bits_metodo2(bits_tx_m2)
        self.assertTrue(rel_m2["sucesso"])
        self.assertEqual(rel_m2["mensagem"], msg)

    # --------------------------------------------------------------------------
    # REQUISITO 4: MENSAGEM MAIOR
    # --------------------------------------------------------------------------
    def test_req_04_mensagem_maior(self):
        """Requisito 4: Transmissão de mensagem de maior porte."""
        msg_longa = "REDES DE COMPUTADORES 2026 - CAMADA FISICA"
        bits_tx = codificar_mensagem_metodo2(msg_longa)
        
        # Simula canal FSK
        audio = sintetizar_bits_fsk(bits_tx)
        bits_rx = decodificar_audio_fsk(audio, quantidade_bits=len(bits_tx))
        rel = decodificar_bits_metodo2(bits_rx)
        
        self.assertTrue(rel["sucesso"])
        self.assertEqual(rel["mensagem"], msg_longa)
        self.assertEqual(rel["total_bytes_pacote"], len(msg_longa) + 2)


if __name__ == "__main__":
    unittest.main()
