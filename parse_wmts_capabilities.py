import ast
import requests
from xml.etree import ElementTree

CONSOLE_OUTPUT = False

class WMTSPyramidParser:

    def __init__(self, get_cap_url, matrix_set_code):
        self.get_cap_url = get_cap_url
        self.matrix_set_code = matrix_set_code
        self.root = self.get_cap()
        self.zoom_levels = []
        self.top_left_corner = []

    def get_tag(self, element):
        return element.tag.split("}")[1]

    def get_text(self, element):
        try:
            text = element.text.strip()
        except AttributeError:
            return ""
        return self.cast_element(text)

    def cast_element(self, text):
        if "_" not in text:
            try:
                return ast.literal_eval(text)
            except (SyntaxError, ValueError):
                return text
        return text

    def get_subelement(self, element, counter, matrix_set_found, store_data):
        counter += 1
        for subelement in element:
            tag = self.get_tag(subelement)
            text = self.get_text(subelement)
            if store_data:
                self.zoom_levels[-1][tag] = text
            if (not matrix_set_found) and (tag == "Identifier") and (text == self.matrix_set_code):
                matrix_set_found = True
            elif matrix_set_found and (tag == "TileMatrix"):
                store_data = True
                self.zoom_levels.append(dict())
            if CONSOLE_OUTPUT:
                print(f"{counter * ' '}{tag}: {text}")
            self.get_subelement(subelement, counter, matrix_set_found, store_data)

    def get_cap(self):
        response = requests.get(self.get_cap_url)
        return ElementTree.fromstring(response.content)

    def parse(self):
        counter = 0
        matrix_set_found = False
        store_data = False
        for element in self.root:
            if CONSOLE_OUTPUT:
                print(self.get_tag(element))
            self.get_subelement(element, counter, matrix_set_found, store_data)
        self.top_left_corner = [float(coord) for coord in self.zoom_levels[0]["TopLeftCorner"].split(" ")]

    def compute_resolutions(self):
        circumference = 2 * self.top_left_corner[1]
        for zoom_level in self.zoom_levels:
            zoom_level["Resolution"] = circumference / (zoom_level["TileWidth"]*zoom_level["MatrixWidth"])

    def print_resolutions(self):
        print(f"Zoom level | Scale denominator | Resolution")
        for zoom_level in self.zoom_levels:
            print(f"{zoom_level['Identifier']} | {zoom_level['ScaleDenominator']} | {zoom_level['Resolution']}")


parser = WMTSPyramidParser("https://wmts10.geo.admin.ch/EPSG/3857/1.0.0/WMTSCapabilities.xml", "3857_18")
parser.parse()
parser.compute_resolutions()
parser.print_resolutions()