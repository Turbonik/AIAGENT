import math

class Vector:
    def __init__(self, *args):
        if len(args) == 1 and isinstance(args[0], list):
            self.coordinates = args[0]
        else:
            self.coordinates = list(args)

    def length(self):
        # Calculate the Euclidean length of the vector
        return math.sqrt(sum([coord**2 for coord in self.coordinates]))

    def normalize(self):
        # Normalize the vector to have a length of 1
        if self.length() == 0:
            raise ValueError("Cannot normalize a zero vector")
        normalized_vector = [coord / self.length() for coord in self.coordinates]
        return Vector(normalized_vector)

    def dot(self, other):
        # Calculate the dot product of two vectors
        return sum([self.coordinates[i] * other.coordinates[i] for i in range(len(self.coordinates))])

    def cross(self, other):
        # Calculate the cross product of two vectors
        if len(self.coordinates) != 3 or len(other.coordinates) != 3:
            raise ValueError("Cross product is only defined for 3D vectors")
        x = self.coordinates[1] * other.coordinates[2] - self.coordinates[2] * other.coordinates[1]
        y = self.coordinates[2] * other.coordinates[0] - self.coordinates[0] * other.coordinates[2]
        z = self.coordinates[0] * other.coordinates[1] - self.coordinates[1] * other.coordinates[0]
        return Vector(x, y, z)

# Geometry class
class Geometry:
    @staticmethod
    def distance(A, B):
        # Calculate the Euclidean distance between two vectors A and B
        return math.sqrt(sum([(A[i] - B[i])**2 for i in range(len(A))]))

    @staticmethod
    def triangle_area(A, B, C):
        # Calculate the area of a triangle given its vertices A, B, and C
        # Using Heron's formula: Area = sqrt(s * (s - AB) * (s - BC) * (s - CA))
        s = (A.length() + B.length() + C.length()) / 2
        area = math.sqrt(s * (s - A.length()) * (s - B.length()) * (s - C.length()))
        return area

    @staticmethod
    def angle(A, B, C):
        # Calculate the angle between vectors A and B in degrees
        # Using the dot product formula: cos(theta) = A . B / |A| |B|
        # Then, theta = arccos(cos(theta)) * (180 / pi)
        dot_product = A.dot(B)
        magnitude_A = A.length()
        magnitude_B = B.length()
        angle_rad = math.acos(dot_product / (magnitude_A * magnitude_B))
        angle_degrees = math.degrees(angle_rad)
        return angle_degrees

# main.py
from geometry import Geometry
from geometry import Vector
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