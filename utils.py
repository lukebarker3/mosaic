import logging


class MosaicArgs:
    image_to_recreate: str = ""
    tiles_directory: str = ""
    tile_dimensions: int = 50
    tile_matching_resolution: int = 5
    enlargement: int = 8

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            self.__dict__[k] = v

    @staticmethod
    def from_namespace(namespace):
        """
        Maps a pyCLI Namespace to a MoogleArgs.
        
        Args:
            namespace (Namespace): The Namespace instance to map.
        
        Returns:
            MoogleArgs: The mapped MoogleArgs instance.
        """
        namespace_dict = vars(namespace)
        return MosaicArgs(**namespace_dict)

def parse_log_level(verbose:bool=False):
    return logging.DEBUG if verbose is True else logging.WARNING

def reduce_fraction(numerator: int, denominator: int):
    can_be_reduced = True
    while can_be_reduced:
        for i in range(2, max(numerator, denominator) + 1):
            if numerator % i == 0 and denominator % i == 0:
                numerator = numerator // i
                denominator = denominator // i
                break
        else:
            can_be_reduced = False
    return (numerator, denominator)
