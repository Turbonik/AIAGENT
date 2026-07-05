class Vector:
    def __init__(self, *args):
        if len(args) == 0:
            self.coordinates = [0] * 3
        elif len(args) == 1 and isinstance(args[0], list):
            self.coordinates = args[0]
        else:
            self.coordinates = list(args)

    def length(self):
        return (self.coordinates[0]**2 + self.coordinates[1]**2 + self.coordinates[2]**2)**0.5

    def normalize(self):
        if self.length() == 0:
            raise ValueError("Cannot normalize a zero vector")
        normalized_vector = [coord / self.length() for coord in self.coordinates]
        return Vector(*normalized_vector)

    def dot(self, other):
        return sum(a * b for a, b in zip(self.coordinates, other.coordinates))

    def cross(self, other):
        x = self.coordinates[1] * other.coordinates[2] - self.coordinates[2] * other.coordinates[1]
        y = self.coordinates[2] * other.coordinates[0] - self.coordinates[0] * other.coordinates[2]
        z = self.coordinates[0] * other.coordinates[1] - self.coordinates[1] * other.coordinates[0]
        return Vector(x, y, z)