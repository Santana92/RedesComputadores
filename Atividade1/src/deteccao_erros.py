# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Módulo de Detecção de Erros (Camada de Enlace Lógica).

Implementa:
1. Método 1: Bit de Paridade Par em quadros de 9 bits (8 dados + 1 paridade).
2. Método 2: CRC-8 (Cyclic Redundancy Check) com polinômio padrão ATM/SMBus (0x07).
3. Injeção controlada de erros para fins didáticos e testes de validação.
"""

from typing import List, Tuple, Dict, Any
from .conversao import bytes_para_bits, bits_para_bytes, mensagem_para_bytes, bytes_para_mensagem


# ==============================================================================
# MÉTODO 1: PARIDADE PAR (QUADROS DE 9 BITS)
# ==============================================================================

def calcular_bit_paridade_par(bits_8: List[int]) -> int:
    """
    Calcula o 9º bit de paridade par para um bloco de 8 bits de dados.
    
    Regra da especificação:
    - Se a quantidade de bits '1' nos 8 bits for PAR: bit 9 = 0.
      Exemplo: 11000000 (dois '1's -> par) -> bit 9 = 0.
    - Se a quantidade de bits '1' nos 8 bits for ÍMPAR: bit 9 = 1.
      Exemplo: 11100000 (três '1's -> ímpar) -> bit 9 = 1.
    """
    if len(bits_8) != 8:
        raise ValueError(f"O bloco de dados deve ter exatamente 8 bits, recebido {len(bits_8)}.")
    
    # Aqui contamos a quantidade de bits 1 para definir a paridade par:
    # se a contagem for par, o bit de paridade é 0; se for ímpar, é 1.
    quantidade_uns = sum(bits_8)
    return 0 if (quantidade_uns % 2 == 0) else 1


def criar_quadro_metodo1(bits_8: List[int]) -> List[int]:
    """Cria um quadro de 9 bits: 8 bits de dados + 1 bit de paridade par."""
    # Aqui juntamos os 8 bits de dados do caractere com o 9º bit de paridade
    bit_paridade = calcular_bit_paridade_par(bits_8)
    return list(bits_8) + [bit_paridade]


def codificar_mensagem_metodo1(bits_dados: List[int]) -> List[int]:
    """
    Recebe a lista de bits de dados (múltiplo de 8) e gera a sequência
    de quadros de 9 bits para transmissão.
    """
    if len(bits_dados) % 8 != 0:
        raise ValueError("A quantidade de bits de dados deve ser múltiplo de 8.")
    
    # Dividimos a sequência em blocos de 8 bits e geramos cada quadro de 9 bits
    bits_transmitir = []
    for i in range(0, len(bits_dados), 8):
        bloco_8 = bits_dados[i : i + 8]
        quadro_9 = criar_quadro_metodo1(bloco_8)
        bits_transmitir.extend(quadro_9)
    return bits_transmitir


def verificar_quadro_metodo1(quadro_9: List[int]) -> Tuple[bool, List[int], int, int]:
    """
    Valida um quadro recebido de 9 bits.
    
    Retorna uma tupla:
    (sucesso, bits_dados, paridade_esperada, paridade_recebida)
    """
    if len(quadro_9) != 9:
        raise ValueError(f"O quadro deve ter exatamente 9 bits, recebido {len(quadro_9)}.")
    
    # Aqui separamos os primeiros 8 bits como dados e o 9º como paridade recebida.
    # Em seguida, recalculamos a paridade esperada para comparar com a recebida.
    dados = quadro_9[:8]
    paridade_recebida = quadro_9[8]
    paridade_esperada = calcular_bit_paridade_par(dados)
    
    sucesso = (paridade_esperada == paridade_recebida)
    return sucesso, dados, paridade_esperada, paridade_recebida


def decodificar_quadros_metodo1(bits_recebidos: List[int]) -> Tuple[bool, List[int], List[Dict[str, Any]]]:
    """
    Processa uma sequência completa de bits recebidos no Método 1.
    Agrupa em quadros de 9 bits e verifica cada um.
    
    Retorna:
    - sucesso_global: True se TODOS os quadros foram válidos, False se ao menos um falhou.
    - dados_totais: Lista contendo apenas os bits de dados (8 por quadro).
    - relatorio_quadros: Lista com detalhes de cada quadro para exibição didática.
    """
    total_quadros = len(bits_recebidos) // 9
    dados_totais = []
    relatorio_quadros = []
    sucesso_global = (total_quadros > 0)

    for i in range(total_quadros):
        quadro = bits_recebidos[i * 9 : (i + 1) * 9]
        sucesso, dados, paridade_esperada, paridade_recebida = verificar_quadro_metodo1(quadro)
        
        dados_totais.extend(dados)
        if not sucesso:
            sucesso_global = False
        
        relatorio_quadros.append({
            "quadro_idx": i + 1,
            "quadro_bits": "".join(str(b) for b in quadro),
            "dados_bits": "".join(str(b) for b in dados),
            "paridade_esperada": paridade_esperada,
            "paridade_recebida": paridade_recebida,
            "status": "SUCESSO" if sucesso else "FALHA DE TRANSMISSÃO"
        })

    return sucesso_global, dados_totais, relatorio_quadros


# ==============================================================================
# MÉTODO 2: CRC-8 (CYCLIC REDUNDANCY CHECK)
# ==============================================================================

# Polinômio padrão CRC-8-ATM / SMBus: x^8 + x^2 + x + 1 (0x07)
# Foi escolhido esse polinômio porque é o padrão mais consagrado na literatura para pacotes curtos.
POLINOMIO_CRC8 = 0x07


def calcular_crc8(dados: bytes, polinomio: int = POLINOMIO_CRC8, valor_inicial: int = 0x00) -> int:
    """
    Calcula o código de redundância cíclica de 8 bits (CRC-8) sobre os bytes fornecidos.
    
    Algoritmo:
    Divisão polinomial no corpo de Galois GF(2) com operações XOR e shifts.
    Garante detecção de 100% dos erros simples de bit, erros duplos e rajadas de até 8 bits.
    """
    # Aqui fazemos a divisão polinomial em GF(2) byte a byte com deslocamento e XOR
    crc = valor_inicial
    for byte in dados:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ polinomio) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def montar_pacote_metodo2(dados: bytes) -> bytes:
    """
    Estrutura o pacote de transmissão do Método 2:
    [Byte 0: Comprimento N] + [Bytes 1 a N: Carga Útil (Payload)] + [Byte N+1: CRC-8]
    """
    tamanho = len(dados)
    if tamanho > 255:
        raise ValueError("O tamanho máximo suportado por quadro é de 255 bytes.")
    
    # Decidimos colocar o byte de tamanho no início para o receptor saber exatamente quantos bytes ler
    cabecalho = bytes([tamanho])
    corpo = cabecalho + dados
    crc = calcular_crc8(corpo)
    return corpo + bytes([crc])


def desmontar_pacote_metodo2(pacote: bytes) -> Tuple[bool, bytes, int, int, str]:
    """
    Desmonta e valida o pacote recebido no Método 2.
    
    Retorna uma tupla:
    (sucesso, payload, crc_esperado, crc_recebido, status_formatado)
    """
    if len(pacote) < 2:
        return False, b"", 0, 0, "FALHA DE TRANSMISSÃO — pacote incompleto"
    
    # Aqui lemos o Byte 0 para delimitar o pacote e não misturar com o silêncio gravado no final do áudio
    tamanho_declarado = pacote[0]
    tamanho_esperado = 1 + tamanho_declarado + 1
    
    if len(pacote) < tamanho_esperado:
        return False, b"", 0, 0, f"FALHA DE TRANSMISSÃO — pacote incompleto (recebido {len(pacote)}B, esperado {tamanho_esperado}B)"
    
    pacote_util = pacote[:tamanho_esperado]
    pacote_sem_crc = pacote_util[:-1]
    crc_recebido = pacote_util[-1]
    
    crc_calculado = calcular_crc8(pacote_sem_crc)
    payload = pacote_util[1 : 1 + tamanho_declarado]
    
    # Validações: CRC idêntico e integridade de tamanho do cabeçalho
    sucesso = (crc_calculado == crc_recebido) and (len(payload) == tamanho_declarado)
    
    status = "SUCESSO — dados íntegros" if sucesso else "FALHA DE TRANSMISSÃO — dados corrompidos"
    return sucesso, payload, crc_calculado, crc_recebido, status


def codificar_mensagem_metodo2(mensagem: str) -> List[int]:
    """
    Atalho: converte mensagem de texto em pacote com cabeçalho e CRC-8,
    retornando a sequência completa de bits para transmissão do Método 2 (Duração).
    """
    dados = mensagem_para_bytes(mensagem)
    pacote = montar_pacote_metodo2(dados)
    return bytes_para_bits(pacote)


def decodificar_bits_metodo2(bits: List[int]) -> Dict[str, Any]:
    """
    Decodifica a lista de bits recebidos pelo receptor do Método 2 (Duração),
    valida o CRC-8 e reconstrói o texto original.
    """
    pacote_bytes = bits_para_bytes(bits)
    sucesso, payload, crc_calc, crc_rec, status = desmontar_pacote_metodo2(pacote_bytes)
    texto = bytes_para_mensagem(payload) if sucesso else ""
    
    return {
        "sucesso": sucesso,
        "mensagem": texto,
        "payload_bytes": payload,
        "crc_calculado": hex(crc_calc),
        "crc_recebido": hex(crc_rec),
        "status": status,
        "total_bytes_pacote": len(pacote_bytes)
    }


# ==============================================================================
# INJEÇÃO CONTROLADA DE ERROS (PARA DEMONSTRAÇÕES E TESTES)
# ==============================================================================

def injetar_erro_de_bit(bits: List[int], indice: int = 0) -> List[int]:
    """
    Inverte propositalmente o bit no índice indicado (0 vira 1, 1 vira 0).
    Permite demonstrar a detecção de FALHA DE TRANSMISSÃO com facilidade.
    """
    if not bits:
        return []
    
    # Criamos essa função para inverter deliberadamente 1 bit (0 vira 1 ou 1 vira 0),
    # permitindo demonstrar no vídeo que os mecanismos de paridade e CRC acusam a falha.
    indice_ajustado = indice % len(bits)
    bits_modificados = list(bits)
    bits_modificados[indice_ajustado] = 1 - bits_modificados[indice_ajustado]
    return bits_modificados
