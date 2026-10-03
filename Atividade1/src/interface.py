# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Módulo de Interface Gráfica (Tkinter).

Implementa a interface visual completa do software da Camada Física Acústica:
- Seleção de Método:
  * Método 1: Quantidade de Impactos (0 = 1 batida, 1 = 2 batidas | Paridade Par, quadros de 9 bits)
  * Método 2: Duração do Impacto (0 = curto ~50ms, 1 = longo ~160ms | CRC-8 padrão ATM 0x07)
- Seleção de Papel:
  * Transmissor (TX)
  * Receptor (RX)
  * Transceptor Completo (TX e RX na mesma tela para testes no mesmo PC)
- Para o Método 1:
  * Transmissor: digitação de mensagem, codificação em quadros de 9 bits (8 dados + 1 paridade par),
    exibição completa dos bits, botão para reproduzir impactos no alto-falante,
    opção de injeção de erro de paridade.
  * Receptor: escuta do microfone em tempo real, detecção de 1 batida (0) e 2 batidas (1),
    montagem de quadros de 9 bits, validação de paridade, reconstrução de mensagem
    em modo autônomo (sem mensagem prévia) ou com mensagem de referência opcional,
    calibração de ruído ambiente e controle de sensibilidade.
- Para o Método 2:
  * Transmissor: digitação de mensagem, empacotamento com CRC-8, síntese dos impactos por duração
    (curto = 50 ms para 0, longo = 160 ms para 1), preâmbulo de sincronização e emissão pelo alto-falante.
  * Receptor: captura pelo microfone, detecção de envelope de energia, medição de duração em milissegundos,
    classificação curto/longo via limiar (105 ms), busca de preâmbulo, validação de CRC-8 e reconstrução da mensagem.
"""

import sys
import threading
from typing import Dict, Any, List, Optional
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np

from .conversao import (
    mensagem_para_bits,
    bits_para_mensagem,
    formatar_bits,
    bits_para_bytes,
    bytes_para_bits,
)
from .deteccao_erros import (
    calcular_bit_paridade_par,
    criar_quadro_metodo1,
    verificar_quadro_metodo1,
    codificar_mensagem_metodo1,
    decodificar_quadros_metodo1,
    calcular_crc8,
    montar_pacote_metodo2,
    desmontar_pacote_metodo2,
    codificar_mensagem_metodo2,
    decodificar_bits_metodo2,
    injetar_erro_de_bit,
)
from .metodo1_batidas.transmissor import (
    sintetizar_bits_metodo1,
    transmitir_audio_metodo1,
    parar_transmissao_metodo1,
)
from .metodo1_batidas.receptor import (
    DetectorBatidasTempoReal,
    decodificar_audio_metodo1,
    gravar_audio_microfone,
)
from .metodo2_duracao.transmissor import (
    sintetizar_bits_duracao,
    transmitir_audio_duracao,
    parar_transmissao_duracao,
    calcular_taxa_bps,
    DURACAO_IMPACTO_CURTO,
    DURACAO_IMPACTO_LONGO,
    LIMIAR_DURACAO,
    FREQ_IMPACTO,
)
from .metodo2_duracao.receptor import (
    decodificar_audio_duracao,
    gravar_audio_microfone_duracao,
)


class AppCamadaFisica(tk.Tk):
    """Janela principal da aplicação de Camada Física usando Som."""

    def __init__(self):
        super().__init__()
        self.title("Camada Física usando Som - Redes de Computadores")
        self.geometry("1020x860")
        self.minsize(920, 740)

        # Variáveis de Estado Principais
        self.var_metodo = tk.StringVar(value="metodo1")      # 'metodo1' ou 'metodo2'
        self.var_papel = tk.StringVar(value="tx")            # 'tx', 'rx' ou 'ambos'

        # Variáveis do Transmissor (TX)
        self.var_modo_m1 = tk.StringVar(value="auto")        # 'auto' (alto-falante) ou 'manual' (palmas/batidas no mic)
        self.var_msg_guia_manual = tk.StringVar(value="A")
        self.var_mensagem_tx = tk.StringVar(value="OI")
        self.var_injetar_erro_m1 = tk.BooleanVar(value=False)
        self.var_injetar_erro_m2 = tk.BooleanVar(value=False)
        self.transmitindo_m1 = False
        self.transmitindo_m2 = False
        self.escutando_manual_m1 = False

        # Variáveis do Receptor (RX)
        self.var_msg_ref_rx = tk.StringVar(value="")
        self.var_limiar = tk.DoubleVar(value=0.08)
        self.var_modo_teste_m1 = tk.BooleanVar(value=False)
        self.var_duracao_m2 = tk.DoubleVar(value=10.0)

        # Estado da Recepção em Tempo Real (Método 1)
        self.escutando_tempo_real_m1 = False
        self.bits_recebidos_m1: List[int] = []
        self.historico_impactos_m1: List[str] = []
        self.mensagem_reconstruida_m1 = ""
        self.total_batidas_m1 = 0

        # Histórico de sinais gerados (Método 2)
        self.ultimo_audio_m2: Optional[np.ndarray] = None
        self.ultimos_bits_m2: List[int] = []

        # Instância do Detector de Batidas em Tempo Real (Método 1)
        self.detector_m1 = DetectorBatidasTempoReal(
            callback_bit=self._ao_receber_bit_m1,
            callback_evento=self._ao_receber_evento_m1,
            limiar=self.var_limiar.get(),
            debounce_s=0.085,
            janela_dupla_s=0.35,
        )

        self._construir_layout()
        self._configurar_rastreamento()
        self._atualizar_visibilidade_paineis()
        self._atualizar_detalhes_tx_m1()
        self._atualizar_guia_manual()
        self._atualizar_detalhes_tx_m2()

        # Encerramento gracioso ao fechar
        self.protocol("WM_DELETE_WINDOW", self._ao_fechar)

    def _ao_fechar(self):
        if self.detector_m1.ativo:
            self.detector_m1.parar()
        parar_transmissao_metodo1()
        parar_transmissao_duracao()
        self.destroy()

    def _configurar_rastreamento(self):
        self.var_mensagem_tx.trace_add("write", lambda *_: self._ao_alterar_mensagem_tx())
        self.var_msg_guia_manual.trace_add("write", lambda *_: self._atualizar_guia_manual())
        self.var_msg_ref_rx.trace_add("write", lambda *_: self._ao_alterar_ref_rx())
        self.var_limiar.trace_add("write", lambda *_: self._ao_alterar_limiar())
        self.var_injetar_erro_m1.trace_add("write", lambda *_: self._atualizar_detalhes_tx_m1())
        self.var_injetar_erro_m2.trace_add("write", lambda *_: self._atualizar_detalhes_tx_m2())

    def _ao_alterar_mensagem_tx(self):
        self._atualizar_detalhes_tx_m1()
        self._atualizar_detalhes_tx_m2()

    def _ao_alterar_ref_rx(self):
        ref = self.var_msg_ref_rx.get().strip()
        if ref:
            bits_ref = codificar_mensagem_metodo1(mensagem_para_bits(ref))
            self.lbl_ref_bits_info.config(
                text=f"Referência: '{ref}' -> {len(bits_ref)} bits esperados: {''.join(str(b) for b in bits_ref)}"
            )
        else:
            self.lbl_ref_bits_info.config(
                text="Recepção Livre: Nenhuma mensagem pré-definida. O receptor decodifica qualquer áudio capturado!"
            )

    def _ao_alterar_limiar(self):
        val = self.var_limiar.get()
        self.detector_m1.definir_limiar(val)
        self.lbl_limiar_val.config(text=f"{val:.3f}")

    # ==========================================================================
    # CONSTRUÇÃO DO LAYOUT
    # ==========================================================================
    def _construir_layout(self):
        # 1. Cabeçalho Superior
        frame_header = tk.Frame(self, bg="#0f172a", padx=16, pady=10)
        frame_header.pack(fill=tk.X)

        lbl_titulo = tk.Label(
            frame_header,
            text="CAMADA FÍSICA ACÚSTICA - REDES DE COMPUTADORES",
            font=("Arial", 13, "bold"),
            fg="#f8fafc",
            bg="#0f172a",
        )
        lbl_titulo.pack(anchor="w")

        lbl_sub = tk.Label(
            frame_header,
            text="Comunicação por Áudio Real: Alto-falante → Meio (Ar) → Microfone (Dois Métodos Acústicos)",
            font=("Arial", 9),
            fg="#94a3b8",
            bg="#0f172a",
        )
        lbl_sub.pack(anchor="w")

        # Container Principal
        self.container = ttk.Frame(self, padding="10")
        self.container.pack(fill=tk.BOTH, expand=True)

        # 2. Painel de Seleção de Método e Papel
        frame_topo = ttk.LabelFrame(self.container, text=" 1. Configuração de Operação ", padding="8")
        frame_topo.pack(fill=tk.X, pady=(0, 6))

        # Linha Método
        f_metodo = ttk.Frame(frame_topo)
        f_metodo.pack(fill=tk.X, pady=2)
        ttk.Label(f_metodo, text="Método:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(
            f_metodo,
            text="Método 1 — Quantidade de Impactos (0 = 1 batida, 1 = 2 batidas | Paridade Par, 9 bits)",
            variable=self.var_metodo,
            value="metodo1",
            command=self._ao_trocar_metodo,
        ).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(
            f_metodo,
            text="Método 2 — Duração do Impacto (0 = impacto curto, 1 = impacto longo | CRC-8)",
            variable=self.var_metodo,
            value="metodo2",
            command=self._ao_trocar_metodo,
        ).pack(side=tk.LEFT)

        # Linha Papel
        f_papel = ttk.Frame(frame_topo)
        f_papel.pack(fill=tk.X, pady=2)
        ttk.Label(f_papel, text="Papel:  ", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(
            f_papel,
            text="Transmissor (TX)",
            variable=self.var_papel,
            value="tx",
            command=self._ao_trocar_papel,
        ).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(
            f_papel,
            text="Receptor (RX)",
            variable=self.var_papel,
            value="rx",
            command=self._ao_trocar_papel,
        ).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(
            f_papel,
            text="Transceptor Completo (TX e RX juntos no mesmo computador)",
            variable=self.var_papel,
            value="ambos",
            command=self._ao_trocar_papel,
        ).pack(side=tk.LEFT)

        # 3. Painel Dinâmico Central (Frames de TX e RX dos Métodos)
        self.frame_conteudo = ttk.Frame(self.container)
        self.frame_conteudo.pack(fill=tk.BOTH, expand=False, pady=(0, 6))

        # --- A) MÉTODO 1 - TRANSMISSOR ---
        self.frame_m1_tx = ttk.LabelFrame(
            self.frame_conteudo, text=" 2. Transmissor — Método 1 (Quantidade de Impactos) ", padding="8"
        )
        self._construir_m1_tx()

        # --- B) MÉTODO 1 - RECEPTOR ---
        self.frame_m1_rx = ttk.LabelFrame(
            self.frame_conteudo, text=" 3. Receptor — Método 1 (Escuta em Tempo Real via Microfone) ", padding="8"
        )
        self._construir_m1_rx()

        # --- C) MÉTODO 2 - TRANSMISSOR ---
        self.frame_m2_tx = ttk.LabelFrame(
            self.frame_conteudo, text=" 2. Transmissor — Método 2 (Duração do Impacto) ", padding="8"
        )
        self._construir_m2_tx()

        # --- D) MÉTODO 2 - RECEPTOR ---
        self.frame_m2_rx = ttk.LabelFrame(
            self.frame_conteudo, text=" 3. Receptor — Método 2 (Duração do Impacto via Microfone) ", padding="8"
        )
        self._construir_m2_rx()

        # 4. Banner de Status e Integridade
        self.lbl_status_banner = tk.Label(
            self.container,
            text="Sistema pronto para transmissão ou recepção.",
            font=("Arial", 11, "bold"),
            bg="#f1f5f9",
            fg="#0f172a",
            pady=8,
            relief=tk.GROOVE,
        )
        self.lbl_status_banner.pack(fill=tk.X, pady=(0, 6))

        # 5. Painel de Diagnóstico e Log de Eventos
        frame_log = ttk.LabelFrame(self.container, text=" 4. Diagnóstico em Tempo Real e Log de Eventos ", padding="8")
        frame_log.pack(fill=tk.BOTH, expand=True)

        self.txt_diagnostico = tk.Text(frame_log, height=10, font=("Consolas", 9), wrap=tk.WORD)
        scroll = ttk.Scrollbar(frame_log, orient=tk.VERTICAL, command=self.txt_diagnostico.yview)
        self.txt_diagnostico.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_diagnostico.pack(fill=tk.BOTH, expand=True)

    # --------------------------------------------------------------------------
    # CONSTRUÇÃO DO PAINEL: MÉTODO 1 TX
    # --------------------------------------------------------------------------
    def _construir_m1_tx(self):
        # 1. Seletor de Modo de Transmissão (Automático vs Manual)
        f_modo = ttk.Frame(self.frame_m1_tx)
        f_modo.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(f_modo, text="Forma de Transmissão:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(
            f_modo,
            text="Transmissão Automática (Computador gera impactos no alto-falante)",
            variable=self.var_modo_m1,
            value="auto",
            command=self._ao_alternar_modo_m1,
        ).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(
            f_modo,
            text="Transmissão Manual (Palmas / Batidas na mesa / Caneta / Estalos captados no microfone)",
            variable=self.var_modo_m1,
            value="manual",
            command=self._ao_alternar_modo_m1,
        ).pack(side=tk.LEFT)

        # 2. Subframe: Transmissão Automática
        self.subframe_m1_auto = ttk.Frame(self.frame_m1_tx)

        f_topo = ttk.Frame(self.subframe_m1_auto)
        f_topo.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(f_topo, text="Mensagem a Transmitir:").pack(side=tk.LEFT, padx=(0, 6))
        self.ent_m1_tx = ttk.Entry(f_topo, textvariable=self.var_mensagem_tx, width=24, font=("Consolas", 10))
        self.ent_m1_tx.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Checkbutton(
            f_topo,
            text="Injetar Erro Proposital de Paridade (Inverter 1 Bit)",
            variable=self.var_injetar_erro_m1,
        ).pack(side=tk.LEFT)

        f_botoes = ttk.Frame(self.subframe_m1_auto)
        f_botoes.pack(fill=tk.X, pady=2)

        self.btn_transmitir_batidas = tk.Button(
            f_botoes,
            text="🔊 TRANSMITIR BATIDAS PELO ALTO-FALANTE",
            font=("Arial", 10, "bold"),
            bg="#2563eb",
            fg="white",
            padx=12,
            pady=5,
            command=self._transmitir_m1_auto,
        )
        self.btn_transmitir_batidas.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_parar_batidas = tk.Button(
            f_botoes,
            text="⏹️ Parar Emissão",
            font=("Arial", 9),
            bg="#64748b",
            fg="white",
            padx=8,
            pady=5,
            state=tk.DISABLED,
            command=self._parar_tx_m1,
        )
        self.btn_parar_batidas.pack(side=tk.LEFT)

        self.lbl_detalhes_m1_tx = tk.Label(
            self.subframe_m1_auto,
            text="Quadros de 9 bits: aguardando mensagem...",
            font=("Consolas", 9),
            bg="#f8fafc",
            fg="#0f172a",
            anchor="w",
            justify=tk.LEFT,
            padx=8,
            pady=4,
            relief=tk.RIDGE,
        )
        self.lbl_detalhes_m1_tx.pack(fill=tk.X, pady=(4, 0))

        # 3. Subframe: Transmissão Manual
        self.subframe_m1_manual = ttk.Frame(self.frame_m1_tx)

        lbl_instrucao_manual = tk.Label(
            self.subframe_m1_manual,
            text="✋ TRANSMISSÃO MANUAL: O computador NÃO emite som. Você produz os impactos físicos (palmas, batidas na mesa, estalos de dedos ou clique de caneta) diante do microfone.\nRegra: 1 impacto isolado (•) = Bit 0  |  2 impactos rápidos consecutivos (••) = Bit 1  |  Quadro: 8 bits dados + 1 bit paridade par",
            font=("Arial", 9, "bold"),
            bg="#fef3c7",
            fg="#92400e",
            padx=8,
            pady=4,
            relief=tk.GROOVE,
            justify=tk.LEFT,
            anchor="w",
        )
        lbl_instrucao_manual.pack(fill=tk.X, pady=(0, 4))

        f_ctrl_manual = ttk.Frame(self.subframe_m1_manual)
        f_ctrl_manual.pack(fill=tk.X, pady=(0, 4))

        self.btn_manual_iniciar = tk.Button(
            f_ctrl_manual,
            text="🎙️ INICIAR TRANSMISSÃO MANUAL",
            font=("Arial", 10, "bold"),
            bg="#15803d",
            fg="white",
            padx=12,
            pady=5,
            command=self._iniciar_manual_m1,
        )
        self.btn_manual_iniciar.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_manual_finalizar = tk.Button(
            f_ctrl_manual,
            text="⏹️ FINALIZAR TRANSMISSÃO MANUAL",
            font=("Arial", 10, "bold"),
            bg="#dc2626",
            fg="white",
            padx=12,
            pady=5,
            state=tk.DISABLED,
            command=self._finalizar_manual_m1,
        )
        self.btn_manual_finalizar.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_manual_limpar = tk.Button(
            f_ctrl_manual,
            text="🔄 Reiniciar / Limpar",
            font=("Arial", 9),
            bg="#64748b",
            fg="white",
            padx=8,
            pady=5,
            command=self._limpar_m1_rx,
        )
        self.btn_manual_limpar.pack(side=tk.LEFT, padx=(0, 12))

        ttk.Label(f_ctrl_manual, text="Nível:").pack(side=tk.LEFT, padx=(0, 2))
        self.progress_volume_manual = ttk.Progressbar(f_ctrl_manual, length=60, mode="determinate")
        self.progress_volume_manual.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(f_ctrl_manual, text="Sensibilidade:").pack(side=tk.LEFT, padx=(0, 2))
        self.slider_limiar_manual = ttk.Scale(
            f_ctrl_manual, from_=0.02, to=0.35, variable=self.var_limiar, length=80, orient=tk.HORIZONTAL
        )
        self.slider_limiar_manual.pack(side=tk.LEFT, padx=(0, 4))

        # Guia Opcional de Batidas
        f_guia = ttk.Frame(self.subframe_m1_manual)
        f_guia.pack(fill=tk.X, pady=(2, 4))
        ttk.Label(f_guia, text="Mensagem Guia (opcional):").pack(side=tk.LEFT, padx=(0, 4))
        self.ent_guia_manual = ttk.Entry(f_guia, textvariable=self.var_msg_guia_manual, width=8, font=("Consolas", 9))
        self.ent_guia_manual.pack(side=tk.LEFT, padx=(0, 8))
        self.lbl_guia_manual = ttk.Label(
            f_guia,
            text="Guia de Batidas: calculando...",
            font=("Arial", 8, "italic"),
            foreground="#475569",
        )
        self.lbl_guia_manual.pack(side=tk.LEFT)

        # Painel de Feedback Visual em Tempo Real da Transmissão Manual
        f_feedback = tk.Frame(self.subframe_m1_manual, bg="#f8fafc", padx=8, pady=6, relief=tk.RIDGE, bd=1)
        f_feedback.pack(fill=tk.X, pady=(2, 0))

        f_fb_l1 = tk.Frame(f_feedback, bg="#f8fafc")
        f_fb_l1.pack(fill=tk.X, pady=1)
        self.lbl_manual_ultimo = tk.Label(
            f_fb_l1,
            text="Último Impacto: [ Aguardando início da transmissão manual... ]",
            font=("Consolas", 10, "bold"),
            bg="#f8fafc",
            fg="#475569",
        )
        self.lbl_manual_ultimo.pack(side=tk.LEFT)

        f_fb_l2 = tk.Frame(f_feedback, bg="#f8fafc")
        f_fb_l2.pack(fill=tk.X, pady=1)
        self.lbl_manual_historico = tk.Label(
            f_fb_l2,
            text="Impactos Detectados: (nenhum)",
            font=("Consolas", 9),
            bg="#f8fafc",
            fg="#334155",
        )
        self.lbl_manual_historico.pack(side=tk.LEFT)

        f_fb_l3 = tk.Frame(f_feedback, bg="#f8fafc")
        f_fb_l3.pack(fill=tk.X, pady=1)
        self.lbl_manual_bits = tk.Label(
            f_fb_l3,
            text="Bits Acumulados: nenhum (0/9 bits)",
            font=("Consolas", 10, "bold"),
            bg="#f8fafc",
            fg="#0f172a",
        )
        self.lbl_manual_bits.pack(side=tk.LEFT, padx=(0, 20))

        self.lbl_manual_paridade = tk.Label(
            f_fb_l3,
            text="Paridade: Aguardando 9 bits...",
            font=("Consolas", 9, "bold"),
            bg="#f8fafc",
            fg="#475569",
        )
        self.lbl_manual_paridade.pack(side=tk.LEFT)

        f_fb_l4 = tk.Frame(f_feedback, bg="#f8fafc")
        f_fb_l4.pack(fill=tk.X, pady=1)
        self.lbl_manual_msg = tk.Label(
            f_fb_l4,
            text="Mensagem Reconstruída: \"\"",
            font=("Consolas", 11, "bold"),
            bg="#f8fafc",
            fg="#1d4ed8",
        )
        self.lbl_manual_msg.pack(side=tk.LEFT)

        # Exibe subframe automático por padrão
        self.subframe_m1_auto.pack(fill=tk.X)

    # --------------------------------------------------------------------------
    # CONSTRUÇÃO DO PAINEL: MÉTODO 1 RX
    # --------------------------------------------------------------------------
    def _construir_m1_rx(self):
        f_controles = ttk.Frame(self.frame_m1_rx)
        f_controles.pack(fill=tk.X, pady=(0, 4))

        self.btn_escutar_m1 = tk.Button(
            f_controles,
            text="🎙️ INICIAR ESCUTA DO MICROFONE",
            font=("Arial", 10, "bold"),
            bg="#15803d",
            fg="white",
            padx=12,
            pady=5,
            command=self._alternar_escuta_m1,
        )
        self.btn_escutar_m1.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_calibrar_m1 = tk.Button(
            f_controles,
            text="🎚️ Calibrar Ruído Ambiente",
            font=("Arial", 9),
            bg="#475569",
            fg="white",
            padx=8,
            pady=5,
            command=self._calibrar_ruido_m1,
        )
        self.btn_calibrar_m1.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_limpar_m1 = tk.Button(
            f_controles,
            text="🔄 Reiniciar Recepção",
            font=("Arial", 9),
            bg="#64748b",
            fg="white",
            padx=8,
            pady=5,
            command=self._limpar_m1_rx,
        )
        self.btn_limpar_m1.pack(side=tk.LEFT, padx=(0, 15))

        # Indicador de Volume Instantâneo
        ttk.Label(f_controles, text="Nível:").pack(side=tk.LEFT, padx=(0, 2))
        self.progress_volume = ttk.Progressbar(f_controles, length=70, mode="determinate")
        self.progress_volume.pack(side=tk.LEFT, padx=(0, 15))

        # Ajuste de Sensibilidade (Limiar)
        ttk.Label(f_controles, text="Sensibilidade:").pack(side=tk.LEFT, padx=(0, 4))
        self.slider_limiar = ttk.Scale(
            f_controles, from_=0.02, to=0.35, variable=self.var_limiar, length=90, orient=tk.HORIZONTAL
        )
        self.slider_limiar.pack(side=tk.LEFT, padx=(0, 4))
        self.lbl_limiar_val = ttk.Label(f_controles, text=f"{self.var_limiar.get():.3f}", width=5)
        self.lbl_limiar_val.pack(side=tk.LEFT)

        # Campo de Referência Opcional
        f_ref = ttk.Frame(self.frame_m1_rx)
        f_ref.pack(fill=tk.X, pady=(2, 4))
        ttk.Label(f_ref, text="Mensagem de Referência (opcional):").pack(side=tk.LEFT, padx=(0, 6))
        self.ent_ref_m1 = ttk.Entry(f_ref, textvariable=self.var_msg_ref_rx, width=20, font=("Consolas", 9))
        self.ent_ref_m1.pack(side=tk.LEFT, padx=(0, 10))
        self.lbl_ref_bits_info = ttk.Label(
            f_ref,
            text="Recepção Livre: Nenhuma mensagem pré-definida. O receptor decodifica qualquer áudio capturado!",
            font=("Arial", 8, "italic"),
            foreground="#475569",
        )
        self.lbl_ref_bits_info.pack(side=tk.LEFT)

        # Linha de Impactos Detectados e Bits
        f_impactos = ttk.Frame(self.frame_m1_rx)
        f_impactos.pack(fill=tk.X, pady=(2, 2))

        self.lbl_ultimo_impacto_rx_m1 = ttk.Label(
            f_impactos,
            text="Último Impacto: Aguardando sons...",
            font=("Consolas", 9, "bold"),
            foreground="#0369a1",
        )
        self.lbl_ultimo_impacto_rx_m1.pack(side=tk.LEFT, padx=(0, 15))

        self.lbl_historico_rx_m1 = ttk.Label(
            f_impactos,
            text="Impactos: (nenhum)",
            font=("Consolas", 9),
            foreground="#475569",
        )
        self.lbl_historico_rx_m1.pack(side=tk.LEFT)

        # Informações da Recepção em Andamento
        f_resumo = ttk.Frame(self.frame_m1_rx)
        f_resumo.pack(fill=tk.X, pady=(2, 0))

        self.lbl_bits_rx_m1 = ttk.Label(
            f_resumo, text="Bits Recebidos: nenhum", font=("Consolas", 10, "bold"), foreground="#0f172a"
        )
        self.lbl_bits_rx_m1.pack(side=tk.LEFT, padx=(0, 20))

        self.lbl_msg_rx_m1 = ttk.Label(
            f_resumo, text="Mensagem Reconstruída: \"\"", font=("Consolas", 10, "bold"), foreground="#1d4ed8"
        )
        self.lbl_msg_rx_m1.pack(side=tk.LEFT)

    # --------------------------------------------------------------------------
    # CONSTRUÇÃO DO PAINEL: MÉTODO 2 TX
    # --------------------------------------------------------------------------
    def _construir_m2_tx(self):
        f_txt = ttk.Frame(self.frame_m2_tx)
        f_txt.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(f_txt, text="Mensagem de Texto:").pack(side=tk.LEFT, padx=(0, 6))
        self.ent_m2_tx = ttk.Entry(f_txt, textvariable=self.var_mensagem_tx, width=24, font=("Consolas", 10))
        self.ent_m2_tx.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Checkbutton(
            f_txt,
            text="Injetar Erro Proposital no CRC-8 (1 Bit Invertido)",
            variable=self.var_injetar_erro_m2,
        ).pack(side=tk.LEFT)

        f_btn = ttk.Frame(self.frame_m2_tx)
        f_btn.pack(fill=tk.X, pady=2)

        self.btn_transmitir_m2 = tk.Button(
            f_btn,
            text="🔊 TRANSMITIR VIA DURAÇÃO (ALTO-FALANTE)",
            font=("Arial", 10, "bold"),
            bg="#0369a1",
            fg="white",
            padx=12,
            pady=5,
            command=self._transmitir_m2,
        )
        self.btn_transmitir_m2.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_parar_m2_tx = tk.Button(
            f_btn,
            text="⏹️ Parar",
            font=("Arial", 9),
            bg="#64748b",
            fg="white",
            padx=8,
            pady=5,
            state=tk.DISABLED,
            command=self._parar_tx_m2,
        )
        self.btn_parar_m2_tx.pack(side=tk.LEFT)

        # Rótulo de Detalhes do Método 2 TX
        self.lbl_detalhes_m2_tx = tk.Label(
            self.frame_m2_tx,
            text="Parâmetros: aguardando...",
            font=("Consolas", 9),
            bg="#f8fafc",
            fg="#0f172a",
            anchor="w",
            justify=tk.LEFT,
            padx=8,
            pady=4,
            relief=tk.RIDGE,
        )
        self.lbl_detalhes_m2_tx.pack(fill=tk.X, pady=(4, 0))

    # --------------------------------------------------------------------------
    # CONSTRUÇÃO DO PAINEL: MÉTODO 2 RX
    # --------------------------------------------------------------------------
    def _construir_m2_rx(self):
        f_botoes = ttk.Frame(self.frame_m2_rx)
        f_botoes.pack(fill=tk.X, pady=(0, 4))

        self.btn_receber_m2 = tk.Button(
            f_botoes,
            text="🎙️ CAPTAR ÁUDIO PELO MICROFONE",
            font=("Arial", 10, "bold"),
            bg="#15803d",
            fg="white",
            padx=12,
            pady=5,
            command=self._receber_m2_microfone,
        )
        self.btn_receber_m2.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(f_botoes, text="Tempo de Escuta:").pack(side=tk.LEFT, padx=(0, 4))
        self.spin_dur_m2 = ttk.Spinbox(
            f_botoes, from_=3.0, to=30.0, increment=1.0, textvariable=self.var_duracao_m2, width=5
        )
        self.spin_dur_m2.pack(side=tk.LEFT, padx=(0, 15))

        self.btn_loopback_m2 = tk.Button(
            f_botoes,
            text="⚡ Loopback Método 2 (Teste Local sem Microfone)",
            font=("Arial", 9),
            bg="#64748b",
            fg="white",
            padx=8,
            pady=5,
            command=self._loopback_m2,
        )
        self.btn_loopback_m2.pack(side=tk.LEFT)

        # Informações da Demodulação Método 2
        self.lbl_demod_m2_info = tk.Label(
            self.frame_m2_rx,
            text=f"Duração: Curto ({DURACAO_IMPACTO_CURTO*1000:.0f} ms) = 0 | Longo ({DURACAO_IMPACTO_LONGO*1000:.0f} ms) = 1 | Limiar = {LIMIAR_DURACAO*1000:.0f} ms | CRC-8 | Aguardando captura...",
            font=("Consolas", 9),
            bg="#f8fafc",
            fg="#0f172a",
            anchor="w",
            justify=tk.LEFT,
            padx=8,
            pady=4,
            relief=tk.RIDGE,
        )
        self.lbl_demod_m2_info.pack(fill=tk.X, pady=(2, 0))

    # ==========================================================================
    # VISIBILIDADE DOS PAINÉIS
    # ==========================================================================
    def _ao_trocar_metodo(self):
        self._parar_tudo_se_ativo()
        self._atualizar_visibilidade_paineis()
        self._definir_status(
            f"{'Método 1 Selecionado: Quantidade de Impactos' if self.var_metodo.get() == 'metodo1' else 'Método 2 Selecionado: Duração do Impacto'}",
            "#e0f2fe",
            "#0369a1",
        )

    def _ao_trocar_papel(self):
        self._parar_tudo_se_ativo()
        self._atualizar_visibilidade_paineis()

    def _atualizar_visibilidade_paineis(self):
        metodo = self.var_metodo.get()
        papel = self.var_papel.get()

        # Oculta todos primeiro
        self.frame_m1_tx.pack_forget()
        self.frame_m1_rx.pack_forget()
        self.frame_m2_tx.pack_forget()
        self.frame_m2_rx.pack_forget()

        if metodo == "metodo1":
            if papel in ("tx", "ambos"):
                self.frame_m1_tx.pack(fill=tk.X, pady=(0, 6))
            if papel in ("rx", "ambos"):
                self.frame_m1_rx.pack(fill=tk.X, pady=(0, 6))
        else:
            if papel in ("tx", "ambos"):
                self.frame_m2_tx.pack(fill=tk.X, pady=(0, 6))
            if papel in ("rx", "ambos"):
                self.frame_m2_rx.pack(fill=tk.X, pady=(0, 6))

    def _parar_tudo_se_ativo(self):
        if self.escutando_manual_m1:
            self._finalizar_manual_m1()
        if self.escutando_tempo_real_m1:
            self._alternar_escuta_m1()
        self._parar_tx_m1()
        self._parar_tx_m2()

    def _ao_alternar_modo_m1(self):
        if self.transmitindo_m1:
            self._parar_tx_m1()
        if self.escutando_manual_m1:
            self._finalizar_manual_m1()

        modo = self.var_modo_m1.get()
        if modo == "auto":
            self.subframe_m1_manual.pack_forget()
            self.subframe_m1_auto.pack(fill=tk.X)
            self._definir_status(
                "Método 1 — Modo Automático: o computador emitirá os impactos pelo alto-falante.",
                "#e0f2fe",
                "#0369a1",
            )
        else:
            self.subframe_m1_auto.pack_forget()
            self.subframe_m1_manual.pack(fill=tk.X)
            self._atualizar_guia_manual()
            self._definir_status(
                "Método 1 — Modo Manual: produza palmas ou batidas físicas diante do microfone!",
                "#fef08a",
                "#854d0e",
            )

    def _atualizar_guia_manual(self):
        msg = self.var_msg_guia_manual.get()
        if not hasattr(self, "lbl_guia_manual"):
            return
        if not msg:
            self.lbl_guia_manual.config(
                text="Modo Livre: Você pode produzir qualquer sequência de impactos (1 batida = 0, 2 batidas = 1)!"
            )
            return

        partes = []
        for char in msg[:3]:
            b_char = mensagem_para_bits(char)
            quadro = criar_quadro_metodo1(b_char)
            p = quadro[-1]
            seq_simbolos = " ".join("•" if b == 0 else "••" for b in quadro)
            partes.append(f"'{char}': dados={''.join(str(b) for b in b_char)} | paridade={p} -> [{seq_simbolos}]")

        texto_guia = "Guia de Batidas: " + " | ".join(partes)
        if len(msg) > 3:
            texto_guia += f" (+{len(msg)-3} caracteres)"
        self.lbl_guia_manual.config(text=texto_guia)

    def _iniciar_manual_m1(self):
        try:
            self.detector_m1.definir_limiar(self.var_limiar.get())
            self.detector_m1.iniciar()
            self.escutando_manual_m1 = True
            self.escutando_tempo_real_m1 = True
            self.btn_manual_iniciar.config(state=tk.DISABLED)
            self.btn_manual_finalizar.config(state=tk.NORMAL)
            self.lbl_manual_ultimo.config(text="[ Aguardando impactos... Produza 1 batida (0) ou 2 rápidas (1) ]", fg="#854d0e")
            self._definir_status(
                "🎙️ TRANSMISSÃO MANUAL ATIVA! Produza impactos no microfone (1 batida = 0, 2 batidas = 1)...",
                "#fef08a",
                "#854d0e",
            )
            self._log_diagnostico("\n=== INÍCIO DA TRANSMISSÃO MANUAL (MÉTODO 1) ===")
            self._log_diagnostico("Microfone aberto. Aguardando impactos físicos do usuário...")
            self._log_diagnostico("Regras: 1 impacto isolado (•) = Bit 0 | 2 impactos rápidos (••) = Bit 1")
            self._log_diagnostico("Cada caractere é composto por 9 bits (8 dados + 1 bit de paridade par).")
        except Exception as e:
            messagebox.showerror("Erro de Microfone", f"Não foi possível abrir o microfone:\n{e}")

    def _finalizar_manual_m1(self):
        if self.escutando_manual_m1 or self.detector_m1.ativo:
            self.detector_m1.parar()
            self.escutando_manual_m1 = False
            self.escutando_tempo_real_m1 = False
            self.btn_manual_iniciar.config(state=tk.NORMAL)
            self.btn_manual_finalizar.config(state=tk.DISABLED)

            self._log_diagnostico("\n=== FINALIZAÇÃO DA TRANSMISSÃO MANUAL (MÉTODO 1) ===")
            self._log_diagnostico(f"Total de bits capturados: {len(self.bits_recebidos_m1)}")
            self._log_diagnostico(f"Sequência de bits:\n{formatar_bits(self.bits_recebidos_m1, 9)}")

            if not self.bits_recebidos_m1:
                self._definir_status("Transmissão manual finalizada. Nenhum impacto sonoro foi registrado.", "#f1f5f9", "#0f172a")
                return

            if len(self.bits_recebidos_m1) >= 9:
                sucesso_global, dados_totais, rel = decodificar_quadros_metodo1(self.bits_recebidos_m1)
                texto = bits_para_mensagem(dados_totais)
                for r in rel:
                    self._log_diagnostico(f"Quadro {r['quadro_idx']}: {r['quadro_bits']} -> Dados: {r['dados_bits']} -> Paridade: {r['paridade_recebida']} (Esperada: {r['paridade_esperada']}) -> {r['status']}")

                if sucesso_global:
                    self._definir_status(f"✓ Transmissão Manual SUCESSO! Mensagem: \"{texto}\"", "#dcfce7", "#166534")
                    self._log_diagnostico(f"[✓ SUCESSO] Mensagem final reconstruída: '{texto}'")
                else:
                    self._definir_status("✗ Transmissão Manual finalizada com falha de paridade.", "#fee2e2", "#991b1b")
                    self._log_diagnostico("[✗ FALHA] Ao menos um quadro apresentou erro de paridade par.")
            else:
                faltam = 9 - len(self.bits_recebidos_m1)
                self._definir_status(f"Transmissão manual finalizada com quadro incompleto ({len(self.bits_recebidos_m1)}/9 bits). Faltaram {faltam} bits.", "#fef08a", "#854d0e")
                self._log_diagnostico(f"Quadro incompleto: apenas {len(self.bits_recebidos_m1)} de 9 bits recebidos.")

    def _definir_status(self, texto: str, cor_fundo: str = "#f1f5f9", cor_texto: str = "#0f172a"):
        self.lbl_status_banner.config(text=texto, bg=cor_fundo, fg=cor_texto)

    def _log_diagnostico(self, texto: str, limpar: bool = False):
        if limpar:
            self.txt_diagnostico.delete("1.0", tk.END)
        self.txt_diagnostico.insert(tk.END, texto + "\n")
        self.txt_diagnostico.see(tk.END)

    # ==========================================================================
    # MÉTODO 1 — LÓGICA DO TRANSMISSOR (TX)
    # ==========================================================================
    def _atualizar_detalhes_tx_m1(self):
        msg = self.var_mensagem_tx.get()
        if not msg:
            self.lbl_detalhes_m1_tx.config(text="Digite uma mensagem para gerar os quadros de 9 bits.")
            return

        linhas = ["QUADROS DE 9 BITS PARA TRANSMISSÃO (8 bits de dados + 1 bit de paridade par):"]
        bits_totais = []
        for i, char in enumerate(msg):
            b_char = mensagem_para_bits(char)
            quadro = criar_quadro_metodo1(b_char)
            p = quadro[-1]
            linhas.append(f"  Quadro {i+1} ('{char}') -> Dados: {''.join(str(b) for b in quadro[:8])} | Paridade Par: {p} -> Quadro: {''.join(str(b) for b in quadro)}")
            bits_totais.extend(quadro)

        if self.var_injetar_erro_m1.get() and bits_totais:
            bits_totais[0] = 1 - bits_totais[0]
            linhas.append("  ⚠ [ERRO INJETADO] O 1º bit foi invertido propositalmente para simular falha de paridade!")

        str_totais = "".join(str(b) for b in bits_totais)
        linhas.append(f"Sequência Completa ({len(bits_totais)} bits): {str_totais}")
        linhas.append("Legenda: 1 impacto acústico = Bit 0  |  2 impactos acústicos consecutivos = Bit 1")
        self.lbl_detalhes_m1_tx.config(text="\n".join(linhas))

    def _transmitir_m1_auto(self):
        msg = self.var_mensagem_tx.get().strip() or "OI"
        bits_tx = codificar_mensagem_metodo1(mensagem_para_bits(msg))
        if self.var_injetar_erro_m1.get() and bits_tx:
            bits_tx[0] = 1 - bits_tx[0]

        def tarefa():
            self.transmitindo_m1 = True
            self.after(0, lambda: self.btn_transmitir_batidas.config(state=tk.DISABLED))
            self.after(0, lambda: self.btn_parar_batidas.config(state=tk.NORMAL))
            self._definir_status(f"Sintetizando e emitindo batidas para '{msg}'...", "#fef08a", "#854d0e")

            self._log_diagnostico(f"\n=== TRANSMISSÃO MÉTODO 1 (QUANTIDADE DE IMPACTOS) ===")
            self._log_diagnostico(f"Mensagem: '{msg}' | Total de Bits com Paridade: {len(bits_tx)}")
            self._log_diagnostico(f"Bits:\n{formatar_bits(bits_tx, 9)}")
            if self.var_injetar_erro_m1.get():
                self._log_diagnostico("⚠ [ALERTA] 1 Bit invertido propositalmente para simular falha de paridade!")

            audio = sintetizar_bits_metodo1(bits_tx, sample_rate=44100, tempo_bit=0.7)
            self._definir_status("Transmitindo batidas nos alto-falantes...", "#93c5fd", "#1e3a8a")
            try:
                transmitir_audio_metodo1(audio, sample_rate=44100)
                if self.transmitindo_m1:
                    self._definir_status("✓ Transmissão de batidas concluída!", "#bbf7d0", "#166534")
                    self._log_diagnostico("[✓] Emissão de batidas finalizada.")
            except Exception as e:
                self._definir_status(f"Erro na transmissão: {e}", "#fee2e2", "#991b1b")
                self._log_diagnostico(f"[!] Erro ao emitir som: {e}")
            finally:
                self.transmitindo_m1 = False
                self.after(0, lambda: self.btn_transmitir_batidas.config(state=tk.NORMAL))
                self.after(0, lambda: self.btn_parar_batidas.config(state=tk.DISABLED))

        threading.Thread(target=tarefa, daemon=True).start()

    def _parar_tx_m1(self):
        self.transmitindo_m1 = False
        parar_transmissao_metodo1()
        self.btn_transmitir_batidas.config(state=tk.NORMAL)
        self.btn_parar_batidas.config(state=tk.DISABLED)
        self._definir_status("Transmissão interrompida.", "#f1f5f9", "#475569")
        self._log_diagnostico("[*] Emissão de batidas cancelada.")

    # ==========================================================================
    # MÉTODO 1 — LÓGICA DO RECEPTOR (RX)
    # ==========================================================================
    def _alternar_escuta_m1(self):
        if not self.escutando_tempo_real_m1:
            try:
                self.detector_m1.definir_limiar(self.var_limiar.get())
                self.detector_m1.iniciar()
                self.escutando_tempo_real_m1 = True
                self.btn_escutar_m1.config(text="⏹️ PARAR ESCUTA DO MICROFONE", bg="#dc2626")
                self._definir_status("🎙️ Microfone ATIVO! Escutando impactos no ar...", "#fef08a", "#854d0e")
                self._log_diagnostico("\n[*] Microfone aberto para escuta em tempo real (Método 1)...")
            except Exception as e:
                messagebox.showerror("Erro de Microfone", f"Não foi possível abrir o dispositivo de áudio:\n{e}")
        else:
            self.detector_m1.parar()
            self.escutando_tempo_real_m1 = False
            self.btn_escutar_m1.config(text="🎙️ INICIAR ESCUTA DO MICROFONE", bg="#15803d")
            self._definir_status("Escuta do microfone finalizada.", "#f1f5f9", "#0f172a")
            self._log_diagnostico("[*] Escuta do microfone encerrada.")

    def _calibrar_ruido_m1(self):
        def tarefa():
            self._definir_status("🤫 Silêncio! Medindo o ruído de fundo da sala por 1.5s...", "#fef08a", "#854d0e")
            self._log_diagnostico("\n[*] Iniciando calibração adaptativa de ruído ambiente...")
            try:
                ruido_pico, novo_limiar = self.detector_m1.calibrar_ruido(duracao_s=1.5)
                self.after(0, lambda: self.var_limiar.set(novo_limiar))
                self._definir_status(f"✓ Calibração concluída! Limiar ajustado para {novo_limiar:.3f}.", "#bbf7d0", "#166534")
                self._log_diagnostico(f"[✓] Ruído medido: {ruido_pico:.4f} -> Novo limiar ótimo: {novo_limiar:.4f}")
            except Exception as e:
                self._definir_status(f"Erro na calibração: {e}", "#fee2e2", "#991b1b")
                self._log_diagnostico(f"[!] Falha ao calibrar ruído: {e}")

        threading.Thread(target=tarefa, daemon=True).start()

    def _ao_receber_bit_m1(self, bit: int, descricao: str):
        self.after(0, lambda: self._processar_bit_m1(bit, descricao))

    def _processar_bit_m1(self, bit: int, descricao: str):
        self.bits_recebidos_m1.append(bit)
        simbolo = "•" if bit == 0 else "••"
        self.historico_impactos_m1.append(simbolo)
        self.total_batidas_m1 += (1 if bit == 0 else 2)

        str_formatada = formatar_bits(self.bits_recebidos_m1, 9)
        str_historico = " , ".join(self.historico_impactos_m1[-18:])
        if len(self.historico_impactos_m1) > 18:
            str_historico = "... " + str_historico

        # Atualiza labels do RX
        self.lbl_bits_rx_m1.config(text=f"Bits Recebidos ({len(self.bits_recebidos_m1)}): {str_formatada}")
        if hasattr(self, "lbl_ultimo_impacto_rx_m1"):
            self.lbl_ultimo_impacto_rx_m1.config(text=f"Último Impacto: [ {simbolo} ] -> Bit {bit}")
        if hasattr(self, "lbl_historico_rx_m1"):
            self.lbl_historico_rx_m1.config(text=f"Impactos: {str_historico}")

        # Atualiza labels do Manual TX
        if hasattr(self, "lbl_manual_ultimo"):
            self.lbl_manual_ultimo.config(
                text=f"Último Impacto: [ {simbolo} ] ({descricao}) -> Bit {bit}",
                fg="#15803d" if bit == 1 else "#0369a1"
            )
            self.lbl_manual_historico.config(text=f"Impactos Detectados: {str_historico}")
            progresso_quadro = len(self.bits_recebidos_m1) % 9
            self.lbl_manual_bits.config(text=f"Bits: {str_formatada} ({progresso_quadro}/9 bits no quadro atual)")

        self._log_diagnostico(f"[Bit Recebido] {descricao} -> Bit {bit} | Total Bits: {len(self.bits_recebidos_m1)}")

        # Validação contínua de quadros de 9 bits
        if len(self.bits_recebidos_m1) >= 9 and len(self.bits_recebidos_m1) % 9 == 0:
            quadro_atual_idx = len(self.bits_recebidos_m1) // 9
            quadro_bits = self.bits_recebidos_m1[-9:]
            sucesso, dados, p_esp, p_rec = verificar_quadro_metodo1(quadro_bits)

            char_decodificado = bits_para_mensagem(dados)
            self._log_diagnostico(f"--- Quadro {quadro_atual_idx} Completo: {''.join(str(b) for b in quadro_bits)} ---")
            self._log_diagnostico(f"    Dados: {''.join(str(b) for b in dados)} ('{char_decodificado}')")
            self._log_diagnostico(f"    Paridade: Recebida={p_rec} | Esperada={p_esp} -> {'SUCESSO' if sucesso else 'FALHA DE TRANSMISSÃO'}")

            if not sucesso:
                if hasattr(self, "lbl_manual_paridade"):
                    self.lbl_manual_paridade.config(
                        text=f"✗ FALHA DE TRANSMISSÃO — Quadro {quadro_atual_idx}: Paridade Inválida (esperada {p_esp}, recebida {p_rec})!",
                        fg="#dc2626"
                    )
                self._definir_status(
                    f"✗ FALHA DE TRANSMISSÃO — Paridade Inválida no Quadro {quadro_atual_idx}!",
                    "#fee2e2",
                    "#991b1b",
                )
            else:
                sucesso_global, dados_totais, _ = decodificar_quadros_metodo1(self.bits_recebidos_m1)
                texto = bits_para_mensagem(dados_totais)
                self.lbl_msg_rx_m1.config(text=f"Mensagem Reconstruída: \"{texto}\"")
                if hasattr(self, "lbl_manual_msg"):
                    self.lbl_manual_msg.config(text=f"Mensagem Reconstruída: \"{texto}\"")
                if hasattr(self, "lbl_manual_paridade"):
                    self.lbl_manual_paridade.config(
                        text=f"✓ PARIDADE VÁLIDA (Quadro {quadro_atual_idx}: dados={''.join(str(b) for b in dados)} | paridade={p_rec})",
                        fg="#166534"
                    )
                self._definir_status(f"✓ Quadro {quadro_atual_idx} Válido! Texto parcial: \"{texto}\"", "#dcfce7", "#166534")
        else:
            if hasattr(self, "lbl_manual_paridade"):
                faltam = 9 - (len(self.bits_recebidos_m1) % 9)
                self.lbl_manual_paridade.config(
                    text=f"Aguardando quadro completo de 9 bits (faltam {faltam} bits)...",
                    fg="#475569"
                )

    def _ao_receber_evento_m1(self, tipo: str, info: Dict[str, Any]):
        if tipo == "NIVEL_AUDIO":
            pico = info.get("pico", 0.0)
            limiar = info.get("limiar", 0.08)
            pct = min(100, int((pico / max(0.01, limiar * 1.5)) * 100))
            self.after(0, lambda: self.progress_volume.configure(value=pct))
            if hasattr(self, "progress_volume_manual"):
                self.after(0, lambda: self.progress_volume_manual.configure(value=pct))
        elif tipo == "PRIMEIRA_BATIDA":
            self.after(0, lambda: self._definir_status("🔔 1ª batida detectada! Aguardando janela para 2ª...", "#fef08a", "#854d0e"))
            if hasattr(self, "lbl_manual_ultimo"):
                self.after(0, lambda: self.lbl_manual_ultimo.config(
                    text="🔔 1º impacto detectado! Aguardando 2º impacto rápido...", fg="#b45309"
                ))

    def _limpar_m1_rx(self):
        self.bits_recebidos_m1 = []
        self.historico_impactos_m1 = []
        self.total_batidas_m1 = 0
        self.lbl_bits_rx_m1.config(text="Bits Recebidos: nenhum")
        self.lbl_msg_rx_m1.config(text="Mensagem Reconstruída: \"\"")
        if hasattr(self, "lbl_ultimo_impacto_rx_m1"):
            self.lbl_ultimo_impacto_rx_m1.config(text="Último Impacto: Aguardando sons...")
        if hasattr(self, "lbl_historico_rx_m1"):
            self.lbl_historico_rx_m1.config(text="Impactos: (nenhum)")
        if hasattr(self, "lbl_manual_ultimo"):
            self.lbl_manual_ultimo.config(text="Último Impacto: [ Aguardando início... ]", fg="#475569")
            self.lbl_manual_historico.config(text="Impactos Detectados: (nenhum)")
            self.lbl_manual_bits.config(text="Bits Acumulados: nenhum (0/9 bits)")
            self.lbl_manual_paridade.config(text="Paridade: Aguardando 9 bits...", fg="#475569")
            self.lbl_manual_msg.config(text="Mensagem Reconstruída: \"\"")
        self._definir_status("Recepção reiniciada. Pronto para captar novos sons.", "#f1f5f9", "#0f172a")
        self._log_diagnostico("\n[REINÍCIO] Dados do Método 1 reiniciados.")

    # ==========================================================================
    # MÉTODO 2 — LÓGICA DO TRANSMISSOR (DURAÇÃO TX)
    # ==========================================================================
    def _atualizar_detalhes_tx_m2(self):
        msg = self.var_mensagem_tx.get().strip() or "OI"
        try:
            bits_tx = codificar_mensagem_metodo2(msg)
            if self.var_injetar_erro_m2.get():
                bits_tx = injetar_erro_de_bit(bits_tx, indice=10)

            taxas = calcular_taxa_bps(len(msg) * 8, len(bits_tx), incluir_preambulo=True)
            linhas = [
                f"Modulação por Duração: Bit 0 = {DURACAO_IMPACTO_CURTO*1000:.0f} ms | Bit 1 = {DURACAO_IMPACTO_LONGO*1000:.0f} ms | Limiar = {LIMIAR_DURACAO*1000:.0f} ms",
                f"Mensagem: '{msg}' | Pacote com CRC-8: {len(bits_tx)} bits ({len(bits_tx)//8} bytes)",
                f"Taxa Teórica: {taxas['taxa_teorica_bps']} bps | Taxa Prática: {taxas['taxa_pratica_bps']} bps | Duração Estimada: {taxas['duracao_total_s']}s",
            ]
            if self.var_injetar_erro_m2.get():
                linhas.append("⚠ [ALERTA] Injeção de erro de 1 bit ativada (simular falha no CRC-8)!")
            self.lbl_detalhes_m2_tx.config(text="\n".join(linhas))
        except Exception as e:
            self.lbl_detalhes_m2_tx.config(text=f"Erro ao montar pacote: {e}")

    def _transmitir_m2(self):
        msg = self.var_mensagem_tx.get().strip() or "OI"
        injetar_erro = self.var_injetar_erro_m2.get()

        def tarefa():
            self.transmitindo_m2 = True
            self.after(0, lambda: self.btn_transmitir_m2.config(state=tk.DISABLED))
            self.after(0, lambda: self.btn_parar_m2_tx.config(state=tk.NORMAL))
            self._definir_status(f"Sintetizando impactos por duração para '{msg}'...", "#fef08a", "#854d0e")

            bits_tx = codificar_mensagem_metodo2(msg)
            if injetar_erro:
                bits_tx = injetar_erro_de_bit(bits_tx, indice=10)

            audio = sintetizar_bits_duracao(bits_tx, sample_rate=44100, incluir_preambulo=True)
            self.ultimo_audio_m2 = audio
            self.ultimos_bits_m2 = bits_tx

            self._log_diagnostico(f"\n=== TRANSMISSÃO MÉTODO 2 (DURAÇÃO DO IMPACTO) ===")
            self._log_diagnostico(f"Mensagem: '{msg}' | Bits Totais do Pacote: {len(bits_tx)}")
            self._log_diagnostico(f"Bits (Comprimento + Dados + CRC-8):\n{formatar_bits(bits_tx, 8)}")
            if injetar_erro:
                self._log_diagnostico("⚠ [ALERTA] 1 Bit invertido propositalmente para simular falha no CRC-8!")

            self._definir_status("Transmitindo impactos sonoros nos alto-falantes...", "#93c5fd", "#1e3a8a")
            try:
                transmitir_audio_duracao(audio, sample_rate=44100)
                if self.transmitindo_m2:
                    self._definir_status("✓ Transmissão do Método 2 concluída com sucesso!", "#bbf7d0", "#166534")
                    self._log_diagnostico("[✓] Transmissão do Método 2 finalizada.")
            except Exception as e:
                self._definir_status(f"Erro na transmissão: {e}", "#fee2e2", "#991b1b")
                self._log_diagnostico(f"[!] Erro ao emitir áudio: {e}")
            finally:
                self.transmitindo_m2 = False
                self.after(0, lambda: self.btn_transmitir_m2.config(state=tk.NORMAL))
                self.after(0, lambda: self.btn_parar_m2_tx.config(state=tk.DISABLED))

        threading.Thread(target=tarefa, daemon=True).start()

    def _parar_tx_m2(self):
        self.transmitindo_m2 = False
        parar_transmissao_duracao()
        self.btn_transmitir_m2.config(state=tk.NORMAL)
        self.btn_parar_m2_tx.config(state=tk.DISABLED)
        self._definir_status("Transmissão interrompida.", "#f1f5f9", "#475569")
        self._log_diagnostico("[*] Emissão de áudio cancelada.")

    # ==========================================================================
    # MÉTODO 2 — LÓGICA DO RECEPTOR (DURAÇÃO RX)
    # ==========================================================================
    def _receber_m2_microfone(self):
        duracao = float(self.var_duracao_m2.get())

        def tarefa():
            self.after(0, lambda: self.btn_receber_m2.config(
                text=f"🎙️ ESCUTANDO ({duracao:.1f}s)...", state=tk.DISABLED, bg="#d97706"
            ))
            self._definir_status(
                f"🎙️ Escutando microfone ({duracao:.1f}s)... AGUARDANDO TRANSMISSÃO (Inicie no PC transmissor!)",
                "#fef08a",
                "#854d0e"
            )
            self._log_diagnostico(f"\n[*] Gravando microfone para o Método 2 ({duracao:.1f} segundos)...")
            self._log_diagnostico("[*] Receptor ativo. Aguardando impactos e preâmbulo (10101010)...")

            try:
                sinal = gravar_audio_microfone_duracao(duracao, sample_rate=44100)
                self._definir_status("🔍 Áudio captado! Analisando duração dos impactos e CRC-8...", "#93c5fd", "#1e3a8a")
                self._processar_m2_recebido(sinal)
            except Exception as e:
                self._definir_status(f"Erro ao capturar áudio: {e}", "#fee2e2", "#991b1b")
                self._log_diagnostico(f"[!] Falha na gravação do microfone: {e}")
            finally:
                self.after(0, lambda: self.btn_receber_m2.config(
                    text="🎙️ CAPTAR ÁUDIO PELO MICROFONE", state=tk.NORMAL, bg="#15803d"
                ))

        threading.Thread(target=tarefa, daemon=True).start()

    def _loopback_m2(self):
        if self.ultimo_audio_m2 is None:
            messagebox.showinfo("Aviso", "Transmita primeiro um sinal do Método 2 para gerar o áudio de loopback.")
            return
        self._log_diagnostico("\n=== TESTE DE LOOPBACK MÉTODO 2 (INTERNO) ===")
        self._processar_m2_recebido(self.ultimo_audio_m2)

    def _processar_m2_recebido(self, sinal: np.ndarray):
        bits_rx, diag = decodificar_audio_duracao(sinal, sample_rate=44100, retornar_diagnostico=True)

        if not bits_rx and not diag.get("impactos"):
            self._log_diagnostico("[!] Nenhum impacto acústico detectado no áudio capturado.")
            self._log_diagnostico("    - Dica: Verifique o volume do alto-falante e se a transmissão ocorreu durante a escuta.")
            self._definir_status("✗ Falha de Recepção: Nenhum impacto sonoro detectado no microfone!", "#fee2e2", "#991b1b")
            self.lbl_demod_m2_info.config(
                text="Método 2: Nenhum impacto detectado no sinal capturado."
            )
            return

        total_imp = diag.get("total_impactos_detectados", 0)
        pre_ok = diag.get("preambulo_detectado", False)
        self._log_diagnostico(f"[+] Total de impactos detectados: {total_imp}")
        self._log_diagnostico(f"[+] Preâmbulo (10101010): {'DETECTADO' if pre_ok else 'NÃO LOCALIZADO'}")

        # Mostra os impactos individuais com tempo e duração medida
        impactos = diag.get("impactos", [])
        if impactos:
            self._log_diagnostico("--- Amostra das Durações dos Impactos ---")
            for imp in impactos[:12]:
                self._log_diagnostico(
                    f"  Impacto {imp['impacto_idx']:02d} [{imp['tempo_inicio_s']:.3f}s]: "
                    f"Duração = {imp['duracao_ms']:5.1f} ms -> {imp['classificacao']} (Bit {imp['bit']})"
                )
            if len(impactos) > 12:
                self._log_diagnostico(f"  ... (+ {len(impactos)-12} impactos medidos)")

        self._log_diagnostico(f"Bits recuperados do pacote ({len(bits_rx)} bits):\n{formatar_bits(bits_rx, 8)}")

        relatorio = decodificar_bits_metodo2(bits_rx)
        self._log_diagnostico(f"CRC-8 Calculado: {relatorio['crc_calculado']} | Recebido: {relatorio['crc_recebido']}")
        self._log_diagnostico(f"Status: {relatorio['status']}")

        info_lbl = f"Duração: {total_imp} impactos | Preâmbulo: {'OK' if pre_ok else 'Não'} | CRC: {relatorio['crc_calculado']} vs {relatorio['crc_recebido']} -> {relatorio['status']}"
        self.lbl_demod_m2_info.config(text=info_lbl)

        if relatorio["sucesso"]:
            msg = relatorio["mensagem"]
            self._log_diagnostico(f"[✓ SUCESSO] Mensagem Reconstruída: '{msg}'")
            self._definir_status(f"✓ SUCESSO — Integridade Validada via CRC-8: '{msg}'", "#22c55e", "white")
        else:
            self._log_diagnostico("[✗ FALHA] Pacote corrompido ou incompleto! O CRC-8 acusou divergência.")
            self._definir_status(f"✗ {relatorio['status']}", "#ef4444", "white")


def iniciar_interface():
    app = AppCamadaFisica()
    app.mainloop()


if __name__ == "__main__":
    iniciar_interface()
