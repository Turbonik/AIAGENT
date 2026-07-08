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