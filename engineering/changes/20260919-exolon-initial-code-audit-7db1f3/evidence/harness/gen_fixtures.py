import os
# Каталог фикстур: по умолчанию рядом с этим файлом; переопределяется TMX_FIXTURES.
fb = os.environ.get('TMX_FIXTURES') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')
os.makedirs(fb, exist_ok=True)
H='<?xml version="1.0" encoding="UTF-8"?>\n'
F={
'f01_foreign_root':H+'<somedata><tileset firstgid="1"/><layer name="L" width="3" height="3"/></somedata>',
'f02_empty_map':H+'<map/>',
'f03_gzip':H+'<map width="2" height="1" tilewidth="32" tileheight="32"><tileset firstgid="1" tilewidth="32" tileheight="32"><image source="tiles.png" width="64" height="32"/></tileset><layer name="L" width="2" height="1"><data encoding="base64" compression="gzip">eJzz</data></layer></map>',
'f04_zlib':H+'<map width="2" height="1" tilewidth="32" tileheight="32"><layer name="L" width="2" height="1"><data encoding="base64" compression="zlib">eJzz</data></layer></map>',
'f05_typo_coord':H+'<map width="4" height="2" tilewidth="32a" tileheight="32"><objectgroup name="o"><object name="piston" x="368" y="17o" width="32" height="80"/><object name="noxy"/><object name="badgid" gid="2a" x="1" y="2"/></objectgroup></map>',
'f06_prop_scope':H+'<map width="1" height="1" tilewidth="32" tileheight="32"><imagelayer name="bg"><image source="a.png"/><properties><property name="fromImageLayer" value="LEAK"/></properties></imagelayer><objectgroup name="og"><properties><property name="fromObjGroup" value="LEAK"/></properties><object name="x" x="0" y="0"/></objectgroup><layer name="tiles" width="1" height="1"><properties><property name="fromLayer" value="DROPPED"/></properties><data encoding="csv">0</data></layer><tileset firstgid="1" name="t" tilewidth="32" tileheight="32"><properties><property name="fromTileset" value="DROPPED"/></properties><image source="tiles.png" width="32" height="32"/></tileset></map>',
'f08_csv_short':H+'<map width="2" height="2" tilewidth="32" tileheight="32"><layer name="L" width="2" height="2"><data encoding="csv">1,2,3</data></layer></map>',
'f09_b64_trunc':H+'<map width="2" height="1" tilewidth="32" tileheight="32"><layer name="L" width="2" height="1"><data encoding="base64">AAAA</data></layer></map>',
'f10_b64_extra':H+'<map width="1" height="1" tilewidth="32" tileheight="32"><layer name="L" width="1" height="1"><data encoding="base64">AAAAAAAAAAAAAAAA</data></layer></map>',
'f11_enc_xml':H+'<map width="1" height="1" tilewidth="32" tileheight="32"><layer name="L" width="1" height="1"><data></data></layer></map>',
'f12_firstgid_far':H+'<map width="1" height="1" tilewidth="32" tileheight="32"><tileset firstgid="500" name="t" tilewidth="32" tileheight="32"><image source="tiles.png" width="64" height="64"/></tileset><layer name="L" width="1" height="1"><data encoding="csv">10</data></layer></map>',
'f13_no_layers':H+'<map width="4" height="5" tilewidth="32" tileheight="32"><objectgroup name="o"><object name="turret" x="64" y="160" width="32" height="32"/></objectgroup></map>',
'f14_unclosed':H+'<map width="1" height="1">',
'f15_empty':'',
'f16_neg_float':H+'<map width="4" height="4" tilewidth="32" tileheight="32"><objectgroup name="o"><object name="n" x="-5" y="3.5" width="32" height="32"/></objectgroup></map>',
'f17_huge_dims':H+'<map width="2" height="2" tilewidth="32" tileheight="32"><layer name="L" width="100000" height="100000"><data encoding="csv">1,2</data></layer></map>',
'f18_zero_layer':H+'<map width="2" height="2" tilewidth="32" tileheight="32"><layer name="L" width="0" height="5"><data encoding="csv"></data></layer><layer name="M" width="2" height="2"><data encoding="csv">1,2,3,4</data></layer></map>',
}
for k, v in F.items():
    with open(os.path.join(fb, k + '.tmx'), 'w', encoding='utf-8') as fh:
        fh.write(v)
print('fixtures',len(F))
