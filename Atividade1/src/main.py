# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Ponto de Entrada Principal (Main).

Permite iniciar a aplicação na Interface Gráfica padrão (Tkinter)
ou no Modo Terminal Interativo (CLI) via argumento '--cli'.
"""

import sys
import argparse

from .interface import iniciar_interface
from .conversao import mensagem_para_bits, bits_para_mensagem, formatar_bits, bits_para_bytes
from .deteccao_erros import (
    criar_quadro_metodo1,
    codificar_mensagem_metodo1,
    decodificar_quadros_metodo1,
    montar_pacote_metodo2,
    codificar_mensagem_metodo2,
    decodificar_bits_metodo2,
    injetar_erro_de_bit,
)
from .metodo1_batidas.transmissor import sintetizar_bits_metodo1, transmitir_audio_metodo1
from .metodo1_batidas.receptor import decodificar_audio_metodo1, gravar_audio_microfone
from .metodo2_duracao.transmissor import (
    sintetizar_bits_duracao,
    transmitir_audio_duracao,
    calcular_taxa_bps,
    DURACAO_IMPACTO_CURTO,
    DURACAO_IMPACTO_LONGO,
    LIMIAR_DURACAO,
)
from .metodo2_duracao.receptor import decodificar_audio_duracao, gravar_audio_microfone_duracao


def menu_terminal():
    """Menu interativo em linha de comando para ambientes sem interface gráfica."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    while True:
        print("\n" + "=" * 68)
        print("    CAMADA FÍSICA USANDO SOM - MODO TERMINAL (CLI)")
        print("=" * 68)
        print("1. Método 1 (Quantidade de Impactos) - Transmissão Automática (Alto-falante)")
        print("2. Método 1 (Quantidade de Impactos) - Transmissão Manual (Palmas / Batidas no Microfone)")
        print("3. Método 1 (Quantidade de Impactos) - Receptor em Tempo Real (Escuta do Microfone)")
        print("4. Método 2 (Duração do Impacto)    - Transmissor (TX: 0=curto, 1=longo | CRC-8)")
        print("5. Método 2 (Duração do Impacto)    - Receptor (RX: Captura do Microfone e Duração)")
        print("6. Teste Loopback Local (Ambos os Métodos sem Microfone)")
        print("0. Sair")
        print("-" * 68)

        opcao = input("Escolha uma opção: ").strip()

        if opcao == "0":
            print("\nEncerrando...")
            break

        elif opcao == "1":
            msg = input("Digite a mensagem para o Método 1 (ex: OI): ").strip() or "OI"
            bits_tx = codificar_mensagem_metodo1(mensagem_para_bits(msg))
            print(f"\n[*] QUADROS DE 9 BITS PARA '{msg}' (8 dados + 1 paridade par):")
            for i, char in enumerate(msg):
                b_char = mensagem_para_bits(char)
                q = criar_quadro_metodo1(b_char)
                print(f"  Quadro {i+1} ('{char}') -> Dados: {''.join(str(b) for b in q[:8])} | Paridade: {q[-1]} -> Quadro: {''.join(str(b) for b in q)}")
            print(f"\nSequência Completa ({len(bits_tx)} bits):\n{formatar_bits(bits_tx, 9)}")
            print("\nLegenda: 1 impacto = Bit 0 (•)  |  2 impactos consecutivos = Bit 1 (••)")

            tocar = input("\nDeseja transmitir as batidas pelo alto-falante agora? (S/N) [S]: ").strip().upper()
            if tocar != "N":
                inj = input("Deseja injetar erro de paridade em 1 bit para teste? (S/N) [N]: ").strip().upper()
                if inj == "S":
                    bits_tx[0] = 1 - bits_tx[0]
                    print("⚠ 1 bit invertido para teste de erro de paridade!")
                print(f"[*] Sintetizando e reproduzindo batidas para '{msg}'...")
                audio = sintetizar_bits_metodo1(bits_tx, sample_rate=44100, tempo_bit=0.7)
                transmitir_audio_metodo1(audio, sample_rate=44100)
                print("[✓] Transmissão de batidas finalizada.")

        elif opcao == "2":
            print("\n" + "=" * 68)
            print("    MÉTODO 1 — TRANSMISSÃO MANUAL (IMPACTOS FÍSICOS NO MICROFONE)")
            print("=" * 68)
            print("O computador NÃO gerará sons pelo alto-falante.")
            print("Você produzirá os impactos fisicamente (palmas, batidas na mesa, estalos ou caneta).")
            print("\nRegras de Codificação:")
            print("  • 1 impacto isolado              = BIT 0 (•)")
            print("  • 2 impactos consecutivos rápidos = BIT 1 (••)")
            print("  • Cada caractere requer 9 bits (8 dados + 1 bit de paridade par).")
            print("  • Intervalo recomendado: aguarde ~0.5s entre cada bit.")

            guia = input("\nDigite um caractere guia para exibir a sequência de batidas (ex: 'A') ou ENTER para livre: ").strip()
            if guia:
                for c in guia[:2]:
                    b_c = mensagem_para_bits(c)
                    q_c = criar_quadro_metodo1(b_c)
                    print(f"\nGuia para '{c}' (ASCII {ord(c)} = {''.join(str(b) for b in b_c)}, Paridade Par = {q_c[-1]}):")
                    for idx_b, bit_val in enumerate(q_c):
                        nome_b = f"Bit {idx_b+1} (Dado)" if idx_b < 8 else f"Bit 9 (Paridade = {bit_val})"
                        simb = "•   (1 impacto isolado)" if bit_val == 0 else "••  (2 impactos rápidos)"
                        print(f"  [{idx_b+1}/9] {nome_b}: Bit {bit_val} -> {simb}")

            input("\nPressione ENTER para INICIAR a escuta do microfone...")

            from .metodo1_batidas.receptor import DetectorBatidasTempoReal

            bits_manuais = []
            simbolos_manuais = []

            def cb_bit(bit: int, desc: str):
                simb = "•" if bit == 0 else "••"
                bits_manuais.append(bit)
                simbolos_manuais.append(simb)
                print(f"\n[IMPACTO DETECTADO] {simb} ({desc}) -> Bit {bit}")
                print(f"  Bits acumulados ({len(bits_manuais)}): {''.join(str(b) for b in bits_manuais)}")
                if len(bits_manuais) % 9 == 0:
                    quadro = bits_manuais[-9:]
                    suc, d, p_esp, p_rec = verificar_quadro_metodo1(quadro)
                    ch = bits_para_mensagem(d)
                    if suc:
                        print(f"  >>> ✓ QUADRO VÁLIDO! Dados: {''.join(str(b) for b in d)} ('{ch}') | Paridade Par: {p_rec} (OK) <<<")
                    else:
                        print(f"  >>> ✗ FALHA DE PARIDADE no quadro! Esperada: {p_esp}, Recebida: {p_rec} <<<")

            def cb_evento(tipo: str, info: dict):
                if tipo == "PRIMEIRA_BATIDA":
                    print("  [detector] 1º impacto detectado... aguardando possível 2º impacto...", end="\r", flush=True)

            detector = DetectorBatidasTempoReal(
                callback_bit=cb_bit,
                callback_evento=cb_evento,
                limiar=0.08,
            )
            try:
                detector.iniciar()
                print("\n[*] Microfone ATIVO! Produza os impactos físicos agora.")
                print("    (Pressione ENTER a qualquer momento para FINALIZAR a transmissão manual)")
                input()
            finally:
                detector.parar()
                print("\n[*] Escuta do microfone encerrada.")

            print(f"\nTotal de bits capturados: {len(bits_manuais)}")
            if bits_manuais:
                print(f"Sequência: {''.join(str(b) for b in bits_manuais)}")
                print(f"Impactos:  {' '.join(simbolos_manuais)}")
                if len(bits_manuais) >= 9:
                    suc_glob, dados_tot, rel = decodificar_quadros_metodo1(bits_manuais)
                    if suc_glob:
                        print(f"\n>>> ✓ SUCESSO: Mensagem Final Reconstruída = '{bits_para_mensagem(dados_tot)}' <<<")
                    else:
                        print("\n>>> ✗ FALHA DE TRANSMISSÃO — Pelo menos um quadro teve paridade inválida. <<<")
                else:
                    print(f"Quadro incompleto: recebidos {len(bits_manuais)} de 9 bits.")

        elif opcao == "3":
            dur = float(input("Duração da escuta em segundos (ex: 8): ").strip() or "8")
            print(f"\n[*] Gravando áudio do microfone por {dur:.1f}s...")
            sinal = gravar_audio_microfone(dur)
            bits_rx, instantes = decodificar_audio_metodo1(sinal)
            print(f"\n[+] Batidas detectadas: {len(instantes)}")
            print(f"[+] Bits recebidos ({len(bits_rx)}):\n{formatar_bits(bits_rx, 9)}")

            if not bits_rx:
                print("⚠ Nenhuma batida detectada no áudio gravado.")
                continue

            sucesso, dados, relatorio = decodificar_quadros_metodo1(bits_rx)
            for r in relatorio:
                print(f"Quadro {r['quadro_idx']}: {r['quadro_bits']} -> Dados: {r['dados_bits']} -> Paridade: {r['paridade_recebida']} (Esperada: {r['paridade_esperada']}) -> {r['status']}")

            if sucesso:
                print(f"\n>>> ✓ SUCESSO: Mensagem Reconstruída = '{bits_para_mensagem(dados)}' <<<")
            else:
                print("\n>>> ✗ FALHA DE TRANSMISSÃO — Verificação de paridade acusou erro ou quadro incompleto <<<")

        elif opcao == "4":
            msg = input("Digite a mensagem para o Método 2 (ex: OI): ").strip() or "OI"
            bits_tx = codificar_mensagem_metodo2(msg)

            inj = input("Deseja injetar erro no CRC-8? (S/N) [N]: ").strip().upper()
            if inj == "S":
                bits_tx = injetar_erro_de_bit(bits_tx, indice=10)
                print("⚠ 1 bit invertido para teste de detecção de erro no CRC-8!")

            print(f"\n[*] Pacote Método 2 (Comprimento + Dados + CRC-8): {len(bits_tx)} bits")
            print(f"Bits a transmitir:\n{formatar_bits(bits_tx, 8)}")
            print(f"Legenda: Impacto Curto ({DURACAO_IMPACTO_CURTO*1000:.0f} ms) = 0 | Impacto Longo ({DURACAO_IMPACTO_LONGO*1000:.0f} ms) = 1")
            print(f"Limiar de decisão do receptor: {LIMIAR_DURACAO*1000:.0f} ms")

            taxas = calcular_taxa_bps(len(msg) * 8, len(bits_tx), incluir_preambulo=True)
            print(f"Taxa Teórica: {taxas['taxa_teorica_bps']} bps | Taxa Prática: {taxas['taxa_pratica_bps']} bps")

            tocar = input("\nDeseja transmitir os impactos pelo alto-falante agora? (S/N) [S]: ").strip().upper()
            if tocar != "N":
                print(f"[*] Sintetizando e reproduzindo áudio para '{msg}'...")
                audio = sintetizar_bits_duracao(bits_tx, sample_rate=44100, incluir_preambulo=True)
                print("[*] Transmitindo sinal nos alto-falantes...")
                transmitir_audio_duracao(audio, sample_rate=44100)
                print("[✓] Transmissão do Método 2 concluída com sucesso!")

        elif opcao == "5":
            dur = float(input("Duração da escuta em segundos (ex: 12): ").strip() or "12")
            print(f"\n[*] Gravando áudio do microfone por {dur:.1f}s... (Inicie a transmissão no outro computador)")
            sinal = gravar_audio_microfone_duracao(dur, sample_rate=44100)
            bits_rx, diag = decodificar_audio_duracao(sinal, sample_rate=44100, retornar_diagnostico=True)

            print(f"\n[+] Total de impactos detectados: {diag['total_impactos_detectados']}")
            print(f"[+] Preâmbulo localizado: {'SIM' if diag['preambulo_detectado'] else 'NÃO'}")

            # Debug detalhado de cada impacto detectado
            if diag["impactos"]:
                print("\n[*] DIAGNÓSTICO DE DURAÇÃO DE CADA IMPACTO:")
                for imp in diag["impactos"]:
                    print(f"  Impacto {imp['impacto_idx']:02d}: Início = {imp['tempo_inicio_s']:.3f}s | Duração = {imp['duracao_ms']:5.1f} ms -> {imp['classificacao']} (Bit {imp['bit']})")

            print(f"\n[+] Bits do pacote recuperados ({len(bits_rx)} bits):\n{formatar_bits(bits_rx, 8)}")

            rel = decodificar_bits_metodo2(bits_rx)
            print(f"Status do CRC-8: {rel['status']}")
            print(f"CRC Esperado/Calculado: {rel['crc_calculado']} | Recebido: {rel['crc_recebido']}")
            if rel["sucesso"]:
                print(f"\n>>> ✓ SUCESSO: Mensagem Reconstruída = '{rel['mensagem']}' <<<")
            else:
                print(f"\n>>> ✗ {rel['status']} <<<")

        elif opcao == "6":
            print("\n--- Executando Teste Loopback Local (sem microfone) ---")
            msg = "OI"
            # Método 1
            b1_tx = codificar_mensagem_metodo1(mensagem_para_bits(msg))
            a1 = sintetizar_bits_metodo1(b1_tx, tempo_bit=0.6)
            b1_rx, _ = decodificar_audio_metodo1(a1)
            suc1, d1, _ = decodificar_quadros_metodo1(b1_rx)
            print(f"[Método 1 - Batidas] Enviado '{msg}' -> Recebido: '{bits_para_mensagem(d1)}' -> {'✓ SUCESSO' if suc1 else '✗ FALHA'}")

            # Método 2
            b2_tx = codificar_mensagem_metodo2(msg)
            a2 = sintetizar_bits_duracao(b2_tx, incluir_preambulo=True)
            b2_rx, diag2 = decodificar_audio_duracao(a2, retornar_diagnostico=True)
            rel2 = decodificar_bits_metodo2(b2_rx)
            print(f"[Método 2 - Duração] Enviado '{msg}' -> Recebido: '{rel2['mensagem']}' -> {rel2['status']}")
            print(f"                    CRC Calc: {rel2['crc_calculado']} | CRC Rec: {rel2['crc_recebido']}")


def main():
    parser = argparse.ArgumentParser(description="Software da Camada Física usando Som")
    parser.add_argument("--cli", action="store_true", help="Inicia em modo linha de comando (terminal)")
    args = parser.parse_args()

    if args.cli:
        menu_terminal()
    else:
        iniciar_interface()


if __name__ == "__main__":
    main()
