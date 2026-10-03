# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Testes Unitários e Integrados do Método 1 (Impacto / Batidas).

Cobre:
1. Cálculo de paridade par conforme a especificação oficial.
2. Formação e validação de quadros de 9 bits (corretos e corrompidos).
3. Injeção controlada de erros de bit.
4. Transmissão e recepção acústica simulada (sem ruído e com ruído).
5. Mensagens curtas e remontagem de texto original.
"""

import sys
import os
import unittest
import numpy as np

# Garante que a pasta raiz do projeto esteja no sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.conversao import (
    mensagem_para_bits,
    bits_para_mensagem,
    formatar_bits,
)
from src.deteccao_erros import (
    calcular_bit_paridade_par,
    criar_quadro_metodo1,
    verificar_quadro_metodo1,
    codificar_mensagem_metodo1,
    decodificar_quadros_metodo1,
    injetar_erro_de_bit,
)
from src.metodo1_batidas.transmissor import sintetizar_bits_metodo1
from src.metodo1_batidas.receptor import (
    decodificar_audio_metodo1,
    classificar_batidas_em_bits,
    DetectorBatidasTempoReal,
)


class TestMetodo1(unittest.TestCase):

    def test_01_calculo_paridade_casos_oficiais(self):
        """Valida os exemplos numéricos exatos exigidos pelo professor."""
        # Exemplo 1: 11000000 -> 2 uns (PAR) -> 9º bit deve ser 0
        dados_par = [1, 1, 0, 0, 0, 0, 0, 0]
        self.assertEqual(calcular_bit_paridade_par(dados_par), 0)
        quadro_par = criar_quadro_metodo1(dados_par)
        self.assertEqual(quadro_par, [1, 1, 0, 0, 0, 0, 0, 0, 0])

        # Exemplo 2: 11100000 -> 3 uns (ÍMPAR) -> 9º bit deve ser 1
        dados_impar = [1, 1, 1, 0, 0, 0, 0, 0]
        self.assertEqual(calcular_bit_paridade_par(dados_impar), 1)
        quadro_impar = criar_quadro_metodo1(dados_impar)
        self.assertEqual(quadro_impar, [1, 1, 1, 0, 0, 0, 0, 0, 1])

    def test_02_validacao_quadro_correto_e_corrompido(self):
        """Valida que quadros íntegros retornam SUCESSO e corrompidos retornam FALHA."""
        dados = [0, 1, 0, 0, 0, 0, 0, 1]  # 'A' em ASCII (65) -> 2 uns -> paridade = 0
        quadro = criar_quadro_metodo1(dados)
        
        sucesso, dados_rec, p_calc, p_rec = verificar_quadro_metodo1(quadro)
        self.assertTrue(sucesso, "Quadro íntegro deveria ser validado com SUCESSO.")
        self.assertEqual(dados_rec, dados)
        self.assertEqual(p_calc, 0)
        self.assertEqual(p_rec, 0)

        # Injeta erro no 9º bit (bit de paridade)
        quadro_com_erro = injetar_erro_de_bit(quadro, indice=8)
        sucesso_erro, _, p_calc_e, p_rec_e = verificar_quadro_metodo1(quadro_com_erro)
        self.assertFalse(sucesso_erro, "Quadro alterado deveria acusar FALHA DE TRANSMISSÃO.")
        self.assertNotEqual(p_calc_e, p_rec_e)

    def test_03_injecao_proposital_erro_em_dados(self):
        """Testa inversão proposital de um bit de dado (0 vira 1)."""
        dados = [0, 1, 0, 0, 0, 0, 0, 1]
        quadro = criar_quadro_metodo1(dados)
        
        # Altera o primeiro bit
        quadro_corrompido = injetar_erro_de_bit(quadro, indice=0)
        self.assertEqual(quadro_corrompido[0], 1)
        
        sucesso, _, p_calc, p_rec = verificar_quadro_metodo1(quadro_corrompido)
        self.assertFalse(sucesso, "Inversão de bit de dados deve ser detectada pela paridade.")

    def test_04_transmissao_acustica_sem_ruido(self):
        """Sintetiza áudio de batidas para um quadro e verifica decodificação perfeita."""
        bits_tx = [1, 0, 1, 1, 0, 0, 1, 0, 0]  # Quadro de 9 bits
        audio = sintetizar_bits_metodo1(bits_tx, sample_rate=44100, tempo_bit=0.6)
        
        bits_rx, _ = decodificar_audio_metodo1(audio, sample_rate=44100)
        self.assertEqual(bits_rx, bits_tx, "Os bits demodulados do áudio devem ser idênticos aos transmitidos.")

    def test_05_transmissao_acustica_com_ruido_ambiente(self):
        """Testa a robustez do receptor adicionando ruído estocástico gaussiano ao áudio."""
        bits_tx = [0, 1, 0, 0, 0, 0, 0, 1, 0]
        audio = sintetizar_bits_metodo1(bits_tx, sample_rate=44100, tempo_bit=0.6)
        
        # Adiciona ruído com desvio padrão de 0.03
        np.random.seed(42)
        ruido = np.random.normal(0, 0.03, len(audio)).astype(np.float32)
        audio_ruidoso = audio + ruido
        
        bits_rx, _ = decodificar_audio_metodo1(audio_ruidoso, sample_rate=44100)
        self.assertEqual(bits_rx, bits_tx, "O receptor deve tolerar ruído ambiente e demodular perfeitamente.")

    def test_06_fluxo_completo_mensagem_curta(self):
        """Testa mensagem textual completa: texto -> bits -> quadros 9 bits -> validação -> texto."""
        msg = "OI"
        bits_dados = mensagem_para_bits(msg)
        quadros_tx = codificar_mensagem_metodo1(bits_dados)
        self.assertEqual(len(quadros_tx), 18)  # 2 caracteres * 9 bits = 18 bits
        
        sucesso, dados_rx, relatorio = decodificar_quadros_metodo1(quadros_tx)
        self.assertTrue(sucesso)
        msg_recuperada = bits_para_mensagem(dados_rx)
        self.assertEqual(msg_recuperada, msg)
        self.assertEqual(len(relatorio), 2)
        self.assertEqual(relatorio[0]["status"], "SUCESSO")
        self.assertEqual(relatorio[1]["status"], "SUCESSO")

    def test_07_transmissao_automatica_acustica_oi(self):
        """
        Valida a transmissão automática completa da mensagem 'OI' do Método 1:
        Codificação em 18 bits -> síntese acústica -> demodulação -> validação de paridade -> remontagem.
        """
        msg = "OI"
        bits_tx = codificar_mensagem_metodo1(mensagem_para_bits(msg))
        esperado_18 = [0, 1, 0, 0, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1]
        self.assertEqual(bits_tx, esperado_18, "Os 18 bits de 'OI' com paridade par devem bater com a especificação.")
        
        # Sintetiza o áudio correspondente às batidas automáticas
        audio_batidas = sintetizar_bits_metodo1(bits_tx, sample_rate=44100, tempo_bit=0.6)
        
        # Demodula o áudio capturado
        bits_rx, instantes = decodificar_audio_metodo1(audio_batidas, sample_rate=44100)
        self.assertEqual(bits_rx, bits_tx, "O receptor deve identificar com exatidão todos os 18 bits das batidas emitidas.")
        
        # Validação dos quadros de 9 bits
        sucesso, dados_rx, relatorio = decodificar_quadros_metodo1(bits_rx)
        self.assertTrue(sucesso)
        self.assertEqual(bits_para_mensagem(dados_rx), msg)
        self.assertEqual(relatorio[0]["paridade_recebida"], 1)
        self.assertEqual(relatorio[1]["paridade_recebida"], 1)

    def test_08_entrada_manual_um_impacto_vira_zero(self):
        """Valida que 1 impacto físico isolado é decodificado como bit 0."""
        # 1 único impacto em t = 1.0s
        instantes = [1.0]
        bits = classificar_batidas_em_bits(instantes, limiar_consecutivo=0.35)
        self.assertEqual(bits, [0], "1 impacto isolado DEVE produzir o bit 0.")

    def test_09_entrada_manual_dois_impactos_rapidos_vira_um(self):
        """Valida que 2 impactos físicos consecutivos rápidos são decodificados como bit 1."""
        # 2 impactos rápidos em t = 1.0s e t = 1.15s (delta = 150 ms <= 350 ms)
        instantes = [1.0, 1.15]
        bits = classificar_batidas_em_bits(instantes, limiar_consecutivo=0.35)
        self.assertEqual(bits, [1], "2 impactos rápidos consecutivos DEVEM produzir o bit 1.")

    def test_10_entrada_manual_sequencia_fisica_caractere_a(self):
        """
        Simula a produção física de impactos pelo usuário para transmitir o caractere 'A':
        'A' em ASCII (65) = 01000001
        Cálculo da paridade par: soma dos 1s = 2 (par) -> 9º bit (paridade) = 0
        Quadro de 9 bits resultante: 0, 1, 0, 0, 0, 0, 0, 1, 0
        Sequência física:
          Bit 1 (0): 1 impacto (•)
          Bit 2 (1): 2 impactos rápidos (••)
          Bit 3 (0): 1 impacto (•)
          Bit 4 (0): 1 impacto (•)
          Bit 5 (0): 1 impacto (•)
          Bit 6 (0): 1 impacto (•)
          Bit 7 (0): 1 impacto (•)
          Bit 8 (1): 2 impactos rápidos (••)
          Bit 9 (0): 1 impacto de paridade par (•)
        """
        instantes_produzidos = [
            0.50,         # Bit 1 = 0 (1 impacto)
            1.20, 1.35,   # Bit 2 = 1 (2 impactos rápidos, delta 150 ms)
            2.10,         # Bit 3 = 0 (1 impacto)
            2.80,         # Bit 4 = 0 (1 impacto)
            3.50,         # Bit 5 = 0 (1 impacto)
            4.20,         # Bit 6 = 0 (1 impacto)
            4.90,         # Bit 7 = 0 (1 impacto)
            5.60, 5.75,   # Bit 8 = 1 (2 impactos rápidos, delta 150 ms)
            6.50,         # Bit 9 = 0 (1 impacto - Paridade Par)
        ]

        bits_recuperados = classificar_batidas_em_bits(instantes_produzidos, limiar_consecutivo=0.35)
        esperado_9_bits = [0, 1, 0, 0, 0, 0, 0, 1, 0]
        self.assertEqual(bits_recuperados, esperado_9_bits, "Os 9 bits decodificados dos impactos devem bater exatamente.")

        # Validação do quadro e decodificação do caractere
        sucesso, dados, p_esp, p_rec = verificar_quadro_metodo1(bits_recuperados)
        self.assertTrue(sucesso, "O quadro montado a partir dos impactos manuais deve ser válido na paridade par.")
        self.assertEqual(p_rec, 0)
        self.assertEqual(p_esp, 0)
        self.assertEqual(bits_para_mensagem(dados), "A", "A mensagem recuperada das batidas manuais deve ser 'A'.")

    def test_11_entrada_manual_deteccao_erro_paridade(self):
        """Testa se um erro de batida manual (ex: uma batida a mais gerando bit 1) é detectado pela paridade."""
        # Suponha que o usuário cometeu um erro e o quadro resultante foi [1, 1, 0, 0, 0, 0, 0, 1, 0]
        # (3 uns nos dados, mas paridade veio como 0)
        quadro_com_erro = [1, 1, 0, 0, 0, 0, 0, 1, 0]
        sucesso, dados, p_esp, p_rec = verificar_quadro_metodo1(quadro_com_erro)
        self.assertFalse(sucesso, "Quadro com quantidade ímpar de uns e bit de paridade 0 DEVE acusar falha de paridade.")
        self.assertEqual(p_esp, 1)
        self.assertEqual(p_rec, 0)

    def test_12_detector_tempo_real_estrutura_e_callbacks(self):
        """Verifica se o detector de tempo real instancia, aceita ajuste de limiar e manipula callbacks."""
        bits_captados = []
        detector = DetectorBatidasTempoReal(
            callback_bit=lambda b, d: bits_captados.append(b),
            limiar=0.08,
            debounce_s=0.085,
            janela_dupla_s=0.35,
        )
        self.assertEqual(detector.limiar, 0.08)
        detector.definir_limiar(0.12)
        self.assertAlmostEqual(detector.limiar, 0.12)
        self.assertEqual(detector.estado, "IDLE")
        self.assertFalse(detector.ativo)


if __name__ == "__main__":
    unittest.main()
