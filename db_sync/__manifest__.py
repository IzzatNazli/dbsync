{
    'name': 'DB SYNC',
    'version': '13.0.1.0.1',
    'author': "Precomp"
              ,
    'website': '',
    'license': 'AGPL-3',
    'category': 'ecommerce',
    'depends': [
        'base','sale','sale_stock','account',
    ],
    'data': ['views/views.xml','security/ir.model.access.csv'

    ],
    'auto_install': False,
    'installable': True,
}
