# ./_ct2.py
# -*- coding: utf-8 -*-
# PyXB bindings for NM:328396a68ee5dd74e15c5db7bb93d1ad0a749d9a
# Generated 2025-07-19 14:40:48.838385 by PyXB version 1.2.6 using Python 3.9.23.final.0
# Namespace http://www.thalesgroup.com/rtti/PushPort/CommonTypes/v2 [xmlns:ct2]

from __future__ import unicode_literals
import pyxb
import pyxb.binding
import pyxb.binding.saxer
import io
import pyxb.utils.utility
import pyxb.utils.domutils
import sys
import pyxb.utils.six as _six
# Unique identifier for bindings created at the same time
_GenerationUID = pyxb.utils.utility.UniqueIdentifier('urn:uuid:5c795fca-64ae-11f0-b8d5-7c1e52039c42')

# Version of PyXB used to generate the bindings
_PyXBVersion = '1.2.6'
# Generated bindings are not compatible across PyXB versions
if pyxb.__version__ != _PyXBVersion:
    raise pyxb.PyXBVersionError(_PyXBVersion)

# A holder for module-level binding classes so we can access them from
# inside class definitions where property names may conflict.
_module_typeBindings = pyxb.utils.utility.Object()

# Import bindings for namespaces imported into schema
import pyxb.binding.datatypes

# NOTE: All namespace declarations are reserved within the binding
Namespace = pyxb.namespace.NamespaceForURI('http://www.thalesgroup.com/rtti/PushPort/CommonTypes/v2', create_if_missing=True)
Namespace.configureCategories(['typeBinding', 'elementBinding'])

def CreateFromDocument (xml_text, default_namespace=None, location_base=None):
    """Parse the given XML and use the document element to create a
    Python instance.

    @param xml_text An XML document.  This should be data (Python 2
    str or Python 3 bytes), or a text (Python 2 unicode or Python 3
    str) in the L{pyxb._InputEncoding} encoding.

    @keyword default_namespace The L{pyxb.Namespace} instance to use as the
    default namespace where there is no default namespace in scope.
    If unspecified or C{None}, the namespace of the module containing
    this function will be used.

    @keyword location_base: An object to be recorded as the base of all
    L{pyxb.utils.utility.Location} instances associated with events and
    objects handled by the parser.  You might pass the URI from which
    the document was obtained.
    """

    if pyxb.XMLStyle_saxer != pyxb._XMLStyle:
        dom = pyxb.utils.domutils.StringToDOM(xml_text)
        return CreateFromDOM(dom.documentElement, default_namespace=default_namespace)
    if default_namespace is None:
        default_namespace = Namespace.fallbackNamespace()
    saxer = pyxb.binding.saxer.make_parser(fallback_namespace=default_namespace, location_base=location_base)
    handler = saxer.getContentHandler()
    xmld = xml_text
    if isinstance(xmld, _six.text_type):
        xmld = xmld.encode(pyxb._InputEncoding)
    saxer.parse(io.BytesIO(xmld))
    instance = handler.rootObject()
    return instance

def CreateFromDOM (node, default_namespace=None):
    """Create a Python instance from the given DOM node.
    The node tag must correspond to an element declaration in this module.

    @deprecated: Forcing use of DOM interface is unnecessary; use L{CreateFromDocument}."""
    if default_namespace is None:
        default_namespace = Namespace.fallbackNamespace()
    return pyxb.binding.basis.element.AnyCreateFromDOM(node, default_namespace)


# Atomic simple type: {http://www.thalesgroup.com/rtti/PushPort/CommonTypes/v2}RSIDType
class RSIDType (pyxb.binding.datatypes.string):

    """A Retail Service Identifier. Note that this may be either a full 8-character "portion identifier", or a base 6-character identifier, according to the available information provided to Darwin."""

    _ExpandedName = pyxb.namespace.ExpandedName(Namespace, 'RSIDType')
    _XSDLocation = pyxb.utils.utility.Location('/workspaces/Predicting-UK-Train-Delays-in-Real-Time-and-Classifying-Route-Risk/code/stomp-client-extraction/darwin-env/ppv16/rttiPPTCommonTypes_v2.xsd', 13, 1)
    _Documentation = 'A Retail Service Identifier. Note that this may be either a full 8-character "portion identifier", or a base 6-character identifier, according to the available information provided to Darwin.'
RSIDType._CF_minLength = pyxb.binding.facets.CF_minLength(value=pyxb.binding.datatypes.nonNegativeInteger(6))
RSIDType._CF_maxLength = pyxb.binding.facets.CF_maxLength(value=pyxb.binding.datatypes.nonNegativeInteger(8))
RSIDType._InitializeFacetMap(RSIDType._CF_minLength,
   RSIDType._CF_maxLength)
Namespace.addCategoryObject('typeBinding', 'RSIDType', RSIDType)
_module_typeBindings.RSIDType = RSIDType
