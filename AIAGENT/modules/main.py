# main.py
from vector import Vector
from geometry import Geometry
from utils import VectorParser

def main():
    # Example usage of VectorParser
    parsed_vector = VectorParser.parse("1 2 3")
    print(parsed_vector)

if __name__ == "__main__":
    main()