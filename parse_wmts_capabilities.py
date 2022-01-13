import ast
import requests
from xml.etree import ElementTree

CONSOLE_OUTPUT = False

class WMTSPyramidParser:
    """
    Parser to read a given matrix set from a WMTS XML GetCapabilities document
    and compute the resolution for each zoom level

    Arguments:
        get_cap_url (str): WMTS GetCapabilities URL
            e.g. "https://wmts10.geo.admin.ch/EPSG/3857/1.0.0/WMTSCapabilities.xml"
        matrix_set_code (str): Code of the matrix set to read, e.g. "3857_21"
    
    TODO: Exception handling
    """

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
        """
        Parse the XML and store matrix set definition
        """
        counter = 0
        matrix_set_found = False
        store_data = False
        for element in self.root:
            if CONSOLE_OUTPUT:
                print(self.get_tag(element))
            self.get_subelement(element, counter, matrix_set_found, store_data)
        self.top_left_corner = [float(coord) for coord in self.zoom_levels[0]["TopLeftCorner"].split(" ")]

    def compute_resolutions(self):
        """
        Compute resolution for each zoom level
        """
        for zoom_level in self.zoom_levels:
            zoom_level["Resolution"] = 0.00028 * zoom_level['ScaleDenominator']

    def print_resolutions(self):
        """
        Output the computed resolutions to the console
        """
        print(f"{'Zoom level' : <10} | {'Scale denominator': <17} | {'Resolution'}")
        for zoom_level in self.zoom_levels:
            print(f"{zoom_level['Identifier']: ^10} | {zoom_level['ScaleDenominator']: <17} | {zoom_level['Resolution']}")

# Matrix tile sets:
# swissimage: 3857_21
# ch.swisstopo.pixelkarte-farbe: 3857_19
# ch.swisstopo.pixelkarte-farbe: 3857_19
parser = WMTSPyramidParser("https://wmts10.geo.admin.ch/EPSG/3857/1.0.0/WMTSCapabilities.xml", "3857_21")
parser.parse()
parser.compute_resolutions()
parser.print_resolutions()
