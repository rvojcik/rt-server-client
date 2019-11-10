# Database inicialization
#
import rtapi
import sys
from .. import base

def run(rtobject):
    """Database inicialization. Create some necessary objects in database"""
    
    attribute_map = {
        'CPUs': {
            'object_types': ['Server'],
            'sticky': 'no',
            'attribute_type': 'uint'
        },
        'CPU, MHz': {
            'object_types': ['Server'],
            'sticky': 'no',
            'attribute_type': 'uint'
        },
        'CPU Model': {
            'object_types': ['Server'],
            'sticky': 'no',
            'attribute_type': 'string'
        },
        'CPUs Logical': {
            'object_types': ['Server'],
            'sticky': 'no',
            'attribute_type': 'uint'
        },
        'Cores per CPU': {
            'object_types': ['Server'],
            'sticky': 'no',
            'attribute_type': 'uint'
        },
        'RAM Mem, MB': {
            'object_types': ['Server'],
            'sticky': 'no',
            'attribute_type': 'uint'
        },
        'Installation Date': {
            'object_types': ['Server'],
            'sticky': 'no',
            'attribute_type': 'date'
        },
        'SW type': {
            'object_types': ['Server'],
            'attribute_type': 'dict',
            'sticky': 'no',
            'dict_name': 'server OS type'
        },
        'Kernel': {
            'object_types': ['Server', 'VM'],
            'attribute_type': 'dict',
            'sticky': 'no',
            'dict_name': 'kernels'
        },
        'HW type': {
            'object_types': ['Server'],
            'attribute_type': 'dict',
            'sticky': 'no',
            'dict_name': 'server models'
        },
    }

    for attribute, values in attribute_map.items():
        base.pout("Create Attribute: (%s, %s)" % (values['attribute_type'], attribute))
        # Create Attributes
        try:
            rtobject.CreateAttribute(values['attribute_type'], attribute)
        except:
            e = sys.exc_info()[0]
            base.perr("Unable to create attributes: %s" % (e))
            return False

        # Map Attributes
        for object_type in values['object_types']:
            chapter_id = rtobject.GetDictionaryChapterId('ObjectType')

            if values['attribute_type'] == 'dict':
                dict_chap_id = rtobject.GetDictionaryChapterId(values['dict_name'])

                if not dict_chap_id:
                    base.pout("Creating chapter: (%s)" % (values['dict_name']))
                    rtobject.InsertDictionaryChapter(values['dict_name'])
                    dict_chap_id = rtobject.GetDictionaryChapterId(values['dict_name'])
                base.pout("Map Attribute: (%s -> %s, dict: %s)" % (attribute, object_type, values['dict_name']))
                rtobject.MapAttribute(rtobject.GetDictionaryIdByValue(object_type, chapter_id), rtobject.GetAttributeIdByName(attribute), dict_chap_id, values['sticky'])
            else:
                base.pout("Map Attribute: (%s -> %s)" % (attribute, object_type))
                rtobject.MapAttribute(rtobject.GetDictionaryIdByValue(object_type, chapter_id),rtobject.GetAttributeIdByName(attribute), 'NULL', values['sticky'])

        
    # If we are here, we are done
    return True
        
