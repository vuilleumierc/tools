import ast
import requests
from xml.etree import ElementTree

CONSOLE_OUTPUT = False
OGC_PIXEL_SIZE = 0.00028  # The OGC standard pixel size in meter

GRIDSET_XML_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<gridSet>
"""
GRIDSET_XML_FOOTER = """  <yCoordinateFirst>false</yCoordinateFirst>
  <alignTopLeft>false</alignTopLeft>
  <metersPerUnit>1.0</metersPerUnit>
  <pixelSize>2.8E-4</pixelSize>
</gridSet>"""


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
            if (
                (not matrix_set_found)
                and (tag == "Identifier")
                and (text == self.matrix_set_code)
            ):
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
        self.top_left_corner = [
            float(coord) for coord in self.zoom_levels[0]["TopLeftCorner"].split(" ")
        ]

    def compute_resolutions(self):
        """
        Compute resolution for each zoom level
        """
        for zoom_level in self.zoom_levels:
            zoom_level["Resolution"] = OGC_PIXEL_SIZE * zoom_level["ScaleDenominator"]

    def print_resolutions(self):
        """
        Output the computed resolutions to the console
        """
        print(f"{'Zoom level' : <10} | {'Scale denominator': <17} | {'Resolution'}")
        for zoom_level in self.zoom_levels:
            print(
                f"{zoom_level['Identifier']: ^10} | {zoom_level['ScaleDenominator']: <17} | {zoom_level['Resolution']}"
            )

    def print_scale_denominators(self):
        for zoom_level in self.zoom_levels:
            print(8 * " " + f"<double>{zoom_level['ScaleDenominator']}</double>")

    def compute_bounds(self, zoom_level):
        tile_matrix = self.zoom_levels[zoom_level]
        top_left_corner = tile_matrix["TopLeftCorner"].split(" ")
        scale_denominator = tile_matrix["ScaleDenominator"]
        self.tile_width = tile_matrix["TileWidth"]
        self.tile_height = tile_matrix["TileHeight"]
        matrix_width = tile_matrix["MatrixWidth"]
        matrix_height = tile_matrix["MatrixHeight"]
        pixel_span = scale_denominator * OGC_PIXEL_SIZE
        tile_span_x = self.tile_width * pixel_span
        tile_span_y = self.tile_height * pixel_span

        self.xmin = float(top_left_corner[0])
        self.ymax = float(top_left_corner[1])
        self.xmax = self.xmin + tile_span_x * matrix_width
        self.ymin = self.ymax - tile_span_y * matrix_height
        print(f"Bounds: {self.xmin}, {self.ymin}, {self.xmax}, {self.ymax}")
        print(f"Tile width and height (pixel): {self.tile_width}, {self.tile_height}")

    def print_gridset_xml(self, name, srs_number):
        with open(f"{srs_number}.xml", "w") as xml_file:
            xml_file.write(GRIDSET_XML_HEADER)
            xml_file.write(f"  <name>{name}</name>\n")
            xml_file.write(
                f"""  <srs>
    <number>{srs_number}</number>
  </srs>\n"""
            )

            # Print extent
            xml_file.write(
                f"""  <extent>
    <coords>
      <double>{self.xmin}</double>
      <double>{self.ymin}</double>
      <double>{self.xmax}</double>
      <double>{self.ymax}</double>
    </coords>
  </extent>\n"""
            )

            # Print resolutions
            xml_file.write("  <resolutions>\n")
            for zoom_level in self.zoom_levels:
                xml_file.write(
                    f"    <double>{zoom_level['ScaleDenominator'] * OGC_PIXEL_SIZE}</double>\n"
                )
            xml_file.write("  </resolutions>\n")

            # Print scale names
            xml_file.write("  <scaleNames>\n")
            for zoom_level in self.zoom_levels:
                xml_file.write(
                    f"    <string>{name}:{zoom_level['Identifier']}</string>\n"
                )
            xml_file.write("  </scaleNames>\n")

            xml_file.write(f"  <tileHeight>{self.tile_height}</tileHeight>\n")
            xml_file.write(f"  <tileWidth>{self.tile_width}</tileWidth>\n")
            xml_file.write(GRIDSET_XML_FOOTER)


# Matrix tile sets:
# ch.swisstopo.swissimage: 2056_28
# ch.swisstopo.pixelkarte-farbe: 2056_27
# ch.swisstopo.pixelkarte-grau: 2056_27
EPSG = 21781  # 2056
parser = WMTSPyramidParser(
    f"https://wmts.geo.admin.ch/EPSG/{EPSG}/1.0.0/WMTSCapabilities.xml", f"{EPSG}_28"
)
parser.parse()
parser.compute_bounds(0)
parser.print_scale_denominators()
parser.print_gridset_xml(f"EPSG:{EPSG}", EPSG)
