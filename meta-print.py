import os
from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import GPSTAGS, TAGS
from datetime import datetime
from prettytable import PrettyTable
from textwrap import wrap
from geopy.geocoders import Nominatim

height_label = 'ImageLength'
width_label = 'ImageWidth'
datetime_label = 'DateTime'
orientation_label = 'Orientation'

date_pattern = '%d.%m.%Y %H:%M:%S'
exif_date_pattern = '%Y:%m:%d %H:%M:%S'

cwd = os.getcwd()
source_dir = os.path.join(cwd, 'source')
target_dir = os.path.join(cwd, 'meta')

geolocate_via_rest = True

name = 'Max Mustermann'


def get_exif(file):
    image = Image.open(file)
    image.verify()
    return image._getexif()


def get_labeled_exif(exif):
    labeled = {}
    for (key, val) in exif.items():
        labeled[TAGS.get(key)] = val

    return labeled


def get_geotagging(exif):
    geotagging = {}
    for (idx, tag) in TAGS.items():
        if tag == 'GPSInfo':
            if idx not in exif:
                raise ValueError("No EXIF geotagging found")

            for (key, val) in GPSTAGS.items():
                if key in exif[idx]:
                    geotagging[val] = exif[idx][key]

    return geotagging


def convert_to_decimal(dms, ref):
    degrees = dms[0]
    minutes = dms[1] / 60.0
    seconds = dms[2] / 3600.0

    if ref in ['S', 'W']:
        degrees = -degrees
        minutes = -minutes
        seconds = -seconds

    return round(degrees + minutes + seconds, 5)


def get_coordinates(geotagging):
    lat = convert_to_decimal(geotagging['GPSLatitude'], geotagging['GPSLatitudeRef'])
    lon = convert_to_decimal(geotagging['GPSLongitude'], geotagging['GPSLongitudeRef'])
    return lat, lon


def prettify(dict_to_format):
    t = PrettyTable(border=False, header=False)
    t.field_names = ['key', 'val']
    for key, val in dict_to_format.items():
        t.add_row([key, val])

    t.align['key'] = 'r'
    t.align['val'] = 'l'
    return t.get_string()


def get_location_reversed(lat, lon):
    if geolocate_via_rest:
        locator = Nominatim(user_agent='geocoder')
        return locator.reverse(str(lat) + ', ' + str(lon))
    else:
        return 'foo'


def fix_orientation(image, orientation):
    if orientation == 3:
        return image.rotate(180, expand=True)
    elif orientation == 6:
        return image.rotate(270, expand=True)
    elif orientation == 8:
        return image.rotate(90, expand=True)
    return image


def calculate_text_coordinates(height, width, orientation):
    x_start = width * 0.88
    y_start = height * 0.02

    # switch position when image is in landscape
    if height > width or orientation == 1 or (width > height and orientation == 3):
        x_start = height * 0.83
        y_start = width * 0.02

    return x_start, y_start


def save_with_meta(file, filename):
    exif = get_exif(file)
    labeled_exif = get_labeled_exif(exif)
    geotagging = get_geotagging(exif)

    date = labeled_exif[datetime_label]
    width = labeled_exif[width_label]
    height = labeled_exif[height_label]
    lat, lon = get_coordinates(geotagging)
    location = get_location_reversed(lat, lon)
    date_time = datetime.strptime(date, exif_date_pattern)

    text = prettify({'Name:': name, 'Zeit:': date_time.strftime(date_pattern),
                     'Lat, Lon:': str(lat) + ', ' + str(lon), 'Ort:': '\n'.join(wrap(str(location), 50))})

    orientation = labeled_exif[orientation_label]
    image = Image.open(os.path.join(source_dir, filename))
    image = fix_orientation(image, orientation)
    x_start, y_start = calculate_text_coordinates(height, width, orientation)

    font = ImageFont.truetype("courbd.ttf", 70, encoding="unic")
    image_editable = ImageDraw.Draw(image)
    image_editable.text((y_start, x_start), text, (237, 230, 211), font=font)

    image.save(os.path.join(target_dir, filename))


def main():
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)
    for _, _, files in os.walk(source_dir):
        for file in files:
            print('working on file: ' + file)
            save_with_meta(os.path.join(source_dir, file), file)


if __name__ == '__main__':
    main()
