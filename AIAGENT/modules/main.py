from geometry import Geometry
from vector import Vector
from utils import VectorParser

def main():
    # Create objects of the classes
    point1 = Vector(1, 2, 3)
    point2 = Vector(4, 5, 6)

    # Calculate distance between two points using Geometry class
    distance = Geometry.distance(point1, point2)
    print(f"Distance between {point1} and {point2}: {distance}")

if __name__ == "__main__":
    main()