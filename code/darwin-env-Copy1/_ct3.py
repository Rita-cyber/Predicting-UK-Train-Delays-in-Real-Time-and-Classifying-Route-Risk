# ./_ct3.py
# -*- coding: utf-8 -*-
# PyXB bindings for NM:5839e620c69c15c603a27f5b92b2e59cfa7c4cb1
# Generated 2025-07-19 14:40:48.838071 by PyXB version 1.2.6 using Python 3.9.23.final.0
# Namespace http://www.thalesgroup.com/rtti/PushPort/CommonTypes/v3 [xmlns:ct3]

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
Namespace = pyxb.namespace.NamespaceForURI('http://www.thalesgroup.com/rtti/PushPort/CommonTypes/v3', create_if_missing=True)
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


# Atomic simple type: {http://www.thalesgroup.com/rtti/PushPort/CommonTypes/v3}FormationIDType
class FormationIDType (pyxb.binding.datatypes.string):

    """A unique identifier for a train formation."""

    _ExpandedName = pyxb.namespace.ExpandedName(Namespace, 'FormationIDType')
    _XSDLocation = pyxb.utils.utility.Location('/workspaces/Predicting-UK-Train-Delays-in-Real-Time-and-Classifying-Route-Risk/code/stomp-client-extraction/darwin-env/ppv16/rttiPPTCommonTypes_v3.xsd', 13, 1)
    _Documentation = 'A unique identifier for a train formation.'
FormationIDType._CF_minLength = pyxb.binding.facets.CF_minLength(value=pyxb.binding.datatypes.nonNegativeInteger(1))
FormationIDType._CF_maxLength = pyxb.binding.facets.CF_maxLength(value=pyxb.binding.datatypes.nonNegativeInteger(20))
FormationIDType._InitializeFacetMap(FormationIDType._CF_minLength,
   FormationIDType._CF_maxLength)
Namespace.addCategoryObject('typeBinding', 'FormationIDType', FormationIDType)
_module_typeBindings.FormationIDType = FormationIDType

# Atomic simple type: {http://www.thalesgroup.com/rtti/PushPort/CommonTypes/v3}LoadingValue
class LoadingValue (pyxb.binding.datatypes.unsignedInt):

    """A value representing the loading of a train coach as a percentage (0-100%)."""

    _ExpandedName = pyxb.namespace.ExpandedName(Namespace, 'LoadingValue')
    _XSDLocation = pyxb.utils.utility.Location('/workspaces/Predicting-UK-Train-Delays-in-Real-Time-and-Classifying-Route-Risk/code/stomp-client-extraction/darwin-env/ppv16/rttiPPTCommonTypes_v3.xsd', 22, 1)
    _Documentation = 'A value representing the loading of a train coach as a percentage (0-100%).'
LoadingValue._CF_maxInclusive = pyxb.binding.facets.CF_maxInclusive(value_datatype=LoadingValue, value=pyxb.binding.datatypes.unsignedInt(100))
LoadingValue._InitializeFacetMap(LoadingValue._CF_maxInclusive)
Namespace.addCategoryObject('typeBinding', 'LoadingValue', LoadingValue)
_module_typeBindings.LoadingValue = LoadingValue

# Atomic simple type: {http://www.thalesgroup.com/rtti/PushPort/CommonTypes/v3}CoachNumberType
class CoachNumberType (pyxb.binding.datatypes.string):

    """A Coach number/identifier in a train formation. E.g. "A" or "12"."""

    _ExpandedName = pyxb.namespace.ExpandedName(Namespace, 'CoachNumberType')
    _XSDLocation = pyxb.utils.utility.Location('/workspaces/Predicting-UK-Train-Delays-in-Real-Time-and-Classifying-Route-Risk/code/stomp-client-extraction/darwin-env/ppv16/rttiPPTCommonTypes_v3.xsd', 30, 1)
    _Documentation = 'A Coach number/identifier in a train formation. E.g. "A" or "12".'
CoachNumberType._CF_minLength = pyxb.binding.facets.CF_minLength(value=pyxb.binding.datatypes.nonNegativeInteger(1))
CoachNumberType._CF_maxLength = pyxb.binding.facets.CF_maxLength(value=pyxb.binding.datatypes.nonNegativeInteger(2))
CoachNumberType._InitializeFacetMap(CoachNumberType._CF_minLength,
   CoachNumberType._CF_maxLength)
Namespace.addCategoryObject('typeBinding', 'CoachNumberType', CoachNumberType)
_module_typeBindings.CoachNumberType = CoachNumberType

# Atomic simple type: {http://www.thalesgroup.com/rtti/PushPort/CommonTypes/v3}CoachClassType
class CoachClassType (pyxb.binding.datatypes.string):

    """An indication of the class of a coach in a train formation. E.g. "First", "Standard" or "Mixed"."""

    _ExpandedName = pyxb.namespace.ExpandedName(Namespace, 'CoachClassType')
    _XSDLocation = pyxb.utils.utility.Location('/workspaces/Predicting-UK-Train-Delays-in-Real-Time-and-Classifying-Route-Risk/code/stomp-client-extraction/darwin-env/ppv16/rttiPPTCommonTypes_v3.xsd', 39, 1)
    _Documentation = 'An indication of the class of a coach in a train formation. E.g. "First", "Standard" or "Mixed".'
CoachClassType._InitializeFacetMap()
Namespace.addCategoryObject('typeBinding', 'CoachClassType', CoachClassType)
_module_typeBindings.CoachClassType = CoachClassType
