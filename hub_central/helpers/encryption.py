class Encriptacion:
    # Definimos la lista de constantes como un atributo de clase para no repetirla
    _iConstantes = [78, 79, 82, 77, 65, 76, 75, 69, 89, 78, 79, 82, 77, 65, 76, 75, 69, 89, 78, 79, 82, 77, 65, 76, 75, 69, 89, 78, 79, 82, 77, 65, 76, 75, 69, 89, 78]

    @staticmethod
    def desEncriptar(sEncriptado):
        sReturn = ""
        j = 0

        # Iteramos de 2 en 2, igual que el bucle original
        for i in range(0, len(sEncriptado), 2):
            # Extraemos el par de caracteres hexadecimales
            hex_chunk = sEncriptado[i:i + 2]
            
            # Convertimos de hex a entero (base 16), restamos la constante y convertimos de nuevo a texto
            valor_original = int(hex_chunk, 16) - Encriptacion._iConstantes[j]
            sReturn += chr(valor_original)
            
            j += 1

        return sReturn

    @staticmethod
    def encriptar(sEncriptar):
        sReturn = ""

        for i in range(len(sEncriptar)):
            # Sumamos el valor ASCII del caracter con la constante correspondiente
            valor_calculado = ord(sEncriptar[i]) + Encriptacion._iConstantes[i]
            
            # Convertimos a hexadecimal, quitamos el prefijo '0x' y lo pasamos a mayúsculas
            sReturn += f"{valor_calculado:02X}"

        return sReturn