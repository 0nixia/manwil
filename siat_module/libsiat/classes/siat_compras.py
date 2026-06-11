# import request
# import ..libs.htmlement
from .request import Request
from ..libs import htmlement as html

class SiatCompras:

    def __init__(self):
        pass

    def parse_url(self, url):
        url = 'https://pilotosiat.impuestos.gob.bo/consulta/QR?nit=1265992017&cuf=569F688AE5DB14FDB32FEC32AE2AC793A86B0206A2729EFB8214AFD74&numero=1&t=2'
        req = Request()
        content = req.request(url)
        # print(content)
        tree = html.fromstring(content)
        print(tree)
