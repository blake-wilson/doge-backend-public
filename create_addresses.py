from transaction import block_io
import urllib.request
import qrcode
import qrcode.image.svg


def generate_addresses(num_addresses):
    f = open('addresses', 'w')
    responses = []
    for i in range(0, num_addresses):
        resp = block_io.get_new_address()
        responses.append(resp)
        address = resp['data']['address']
        f.write(address + '\n')

    f.write("\n\n\n")
    for r in responses:
        f.write(repr(r) + "\n")


def generate_qr_codes(f):
    factory = qrcode.image.svg.SvgPathImage

    lines = f.readlines()
    i = 0
    for line in lines:
        if len(line) != 35:
            break
        # Generate QR code
        img = qrcode.make(line[0:34], image_factory=factory)
        img.save('qr_svg_' + str(i) + '.svg')
        i += 1


def add_promos(f):
    lines = f.readlines()
    wallets = set()
    for line in lines:
        if len(line) != 35:
            break
        # Generate QR code
        wallets.add(line[0:34])
    return wallets


def distribute_coins(f):
    from transaction import system_send_doge
    source_address = '9xNVw9mWznyWqCj6crqBWHBku3V3vsSras'
    lines = f.readlines()
    for line in lines:
        # send to adress contained in line
        system_send_doge(source_address, line, 500)
