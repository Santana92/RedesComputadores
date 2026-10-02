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
from .metodo2_fsk.transmissor import sintetizar_bits_fsk, transmitir_audio_fsk, calcular_taxa_bps
from .metodo2_fsk.receptor import decodificar_audio_fsk, gravar_audio_microfone_fsk


def menu_terminal():
    """Menu interativo em linha de comando para ambientes sem interface gráfica."""
    while True:
        print("\n" + "=" * 68)
        print("    CAMADA FÍSICA USANDO SOM - MODO TERMINAL (CLI)")
        print("=" * 68)
        print("1. Método 1 (Batidas) - Transmissor (TX: Automático via Alto-falante ou Guia)")
        print("2. Método 1 (Batidas) - Receptor (RX: Captura do Microfone)")
        print("3. Método 2 (FSK)     - Transmissor (TX: Texto Direto ou Batidas Manuais)")
        print("4. Método 2 (FSK)     - Receptor (RX: Captura do Microfone e Demodulação)")
        print("5. Teste Loopback Local (Ambos os Métodos sem Microfone)")
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
            print("\nLegenda: 1 batida (👏) = Bit 0  |  2 batidas consecutivas (👏👏) = Bit 1")

            tocar = input("\nDeseja transmitir as batidas pelo alto-falante agora? (S/N) [S]: ").strip().upper()
            if tocar != "N":
                inj = input("Deseja injetar erro de paridade em 1 bit para teste? (S/N) [N]: ").strip().upper()
                if inj == "S":
                    bits_tx[0] = 1 - bits_tx[0]
                    print("⚠ 1 bit invertido para teste de erro!")
                print(f"[*] Sintetizando e reproduzindo batidas para '{msg}'...")
                audio = sintetizar_bits_metodo1(bits_tx, sample_rate=44100, tempo_bit=0.7)
                transmitir_audio_metodo1(audio, sample_rate=44100)
                print("[✓] Transmissão de batidas finalizada.")

        elif opcao == "2":
            dur = float(input("Duração da escuta em segundos (ex: 8): ").strip() or "8")
            print(f"\n[*] Gravando áudio do microfone por {dur:.1f}s... (Faça as batidas ou toque pelo alto-falante)")
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

        elif opcao == "3":
            print("\nTipo de entrada para o Transmissor FSK:")
            print("1. Digitar mensagem de texto")
            print("2. Entrada manual por batidas (grava do mic -> converte em bits -> transmite FSK)")
            sub_op = input("Escolha (1/2) [1]: ").strip() or "1"

            if sub_op == "2":
                dur = float(input("Duração da captura de batidas em segundos (ex: 6): ").strip() or "6")
                print(f"[*] Escutando batidas manuais por {dur:.1f}s (1 batida = 0, 2 batidas = 1)...")
                sinal_batidas = gravar_audio_microfone(dur)
                bits_imp, _ = decodificar_audio_metodo1(sinal_batidas)
                print(f"[+] Bits capturados por batidas: {''.join(str(b) for b in bits_imp)} ({len(bits_imp)} bits)")

                if not bits_imp:
                    print("⚠ Nenhuma batida detectada. Operação cancelada.")
                    continue

                # Completa múltiplos de 8 se necessário
                resto = len(bits_imp) % 8
                if resto != 0:
                    bits_imp.extend([0] * (8 - resto))

                dados_bytes = bits_para_bytes(bits_imp)
                pacote = montar_pacote_metodo2(dados_bytes)
                bits_tx = []
                for b in pacote:
                    for s in range(7, -1, -1):
                        bits_tx.append((b >> s) & 1)
                print(f"[*] Pacote FSK gerado com CRC-8: {len(bits_tx)} bits")
            else:
                msg = input("Digite a mensagem para transmitir via FSK (ex: REDE): ").strip() or "REDE"
                bits_tx = codificar_mensagem_metodo2(msg)

            inj = input("Deseja injetar erro no CRC-8? (S/N) [N]: ").strip().upper()
            if inj == "S":
                bits_tx = injetar_erro_de_bit(bits_tx, indice=10)
                print("⚠ 1 bit invertido para teste de CRC-8!")

            print(f"\n[*] Bits FSK ({len(bits_tx)} bits):\n{formatar_bits(bits_tx, 8)}")
            taxas = calcular_taxa_bps(len(bits_tx) - 16, len(bits_tx))
            print(f"[*] Taxa Teórica: {taxas['taxa_teorica_bps']} bps | Prática: {taxas['taxa_pratica_bps']} bps")
            audio = sintetizar_bits_fsk(bits_tx)
            print("[*] Transmitindo sinal FSK no alto-falante...")
            transmitir_audio_fsk(audio)
            print("[✓] Transmissão FSK concluída!")

        elif opcao == "4":
            dur = float(input("Duração da escuta FSK em segundos (ex: 4): ").strip() or "4")
            sinal = gravar_audio_microfone_fsk(dur)
            bits_rx = decodificar_audio_fsk(sinal)
            print(f"\n[+] Bits recebidos ({len(bits_rx)} bits):\n{formatar_bits(bits_rx, 8)}")
            rel = decodificar_bits_metodo2(bits_rx)
            print(f"Status do CRC-8: {rel['status']}")
            print(f"CRC Esperado/Calc: {rel['crc_calculado']} | Recebido: {rel['crc_recebido']}")
            if rel["sucesso"]:
                print(f"\n>>> ✓ SUCESSO: Mensagem = '{rel['mensagem']}' <<<")
            else:
                print(f"\n>>> ✗ {rel['status']} <<<")

        elif opcao == "5":
            print("\n--- Executando Teste Loopback Local (sem microfone) ---")
            msg = "OI"
            # Método 1
            b1_tx = codificar_mensagem_metodo1(mensagem_para_bits(msg))
            a1 = sintetizar_bits_metodo1(b1_tx, tempo_bit=0.6)
            b1_rx, _ = decodificar_audio_metodo1(a1)
            suc1, d1, _ = decodificar_quadros_metodo1(b1_rx)
            print(f"[Método 1] Enviado '{msg}' -> Recebido: '{bits_para_mensagem(d1)}' -> {'✓ SUCESSO' if suc1 else '✗ FALHA'}")

            # Método 2
            b2_tx = codificar_mensagem_metodo2(msg)
            a2 = sintetizar_bits_fsk(b2_tx)
            b2_rx = decodificar_audio_fsk(a2, quantidade_bits=len(b2_tx))
            rel2 = decodificar_bits_metodo2(b2_rx)
            print(f"[Método 2] Enviado '{msg}' -> Recebido: '{rel2['mensagem']}' -> {rel2['status']}")


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
