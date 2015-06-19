from lxml import etree

CELLML_NSMAP = {
    'tmpdoc': 'http://cellml.org/tmp-documentation',
    'pcenv': 'http://www.cellml.org/tools/pcenv/',
    'opencell': 'http://www.cellml.org/tools/opencell/',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
}

uri_prefix = {
    'info:pmid/': 'http://www.ncbi.nlm.nih.gov/pubmed/%s',
    'urn:miriam:pubmed:': 'http://www.ncbi.nlm.nih.gov/pubmed/%s',
}

def uri2http(uri):
    """\
    Resolves an info-uri into an http link based on the lookup table
    above.
    """

    # XXX need a way to normalize these uris into string
    try:
        uri = str(uri)
    except:
        uri = uri.decode('utf8', 'replace')

    for k, v in uri_prefix.iteritems():
        if uri.startswith(k):
            return v % uri[len(k):]
    return None

def normal_kw(input):
    """\
    Method to normalize keywords so we don't have to deal with cases
    when searching and allow the usage of spaces to delimit terms.
    """

    return input.strip().replace(' ', '_').lower()

def fix_pcenv_externalurl(xml, base):
    '''
    A workaround for PCEnv session specification bug
    https://tracker.physiomeproject.org/show_bug.cgi?id=1079

    Briefly, pcenv:externalurl is really a URI reference, but it is
    represented as a literal string, hence it does not benefit from
    the declaration of xml:base.

    This manually replaces externalurl with the xml:base fragment
    inserted in front of it.
    ::

        >>> from cellml.pmr2.util import fix_pcenv_externalurl
        >>> input = \"\"\"<?xml version='1.0' encoding='utf-8'?>
        ... <rdf:RDF
        ...   xmlns:pcenv="http://www.cellml.org/tools/pcenv/"
        ...   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        ... >
        ...  <rdf:Description rdf:about="#ext" pcenv:graphname="example"
        ...    pcenv:externalurl="external.xul"/>
        ... </rdf:RDF>
        ... \"\"\"
        >>> uri = 'http://example.com/'
        >>> uri in input
        False
        >>> output = fix_pcenv_externalurl(input, uri)
        >>> uri + '/external.xul' in output
        True

    Another representation of pcenv:externalurl as a Literal.
    ::

        >>> input = \"\"\"<?xml version='1.0' encoding='utf-8'?>
        ... <rdf:RDF
        ...   xmlns:pcenv="http://www.cellml.org/tools/pcenv/"
        ...   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        ... >
        ...  <rdf:Description rdf:about="#ext">
        ...    <pcenv:graphname>example</pcenv:graphname>
        ...    <pcenv:externalurl>external.xul</pcenv:externalurl>
        ...  </rdf:Description>
        ... </rdf:RDF>
        ... \"\"\"
        >>> uri = 'http://example.com/'
        >>> uri in input
        False
        >>> output = fix_pcenv_externalurl(input, uri)
        >>> uri + '/external.xul' in output
        True

    If the pcenv:externalurl were ever changed to allow URI reference
    along (or replace) with Literals, the node and value shouldn't be
    rewritten.
    ::

        >>> input = \"\"\"<?xml version='1.0' encoding='utf-8'?>
        ... <rdf:RDF
        ...   xmlns:pcenv="http://www.cellml.org/tools/pcenv/"
        ...   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        ... >
        ...  <rdf:Description rdf:about="#ext" pcenv:graphname="example">
        ...    <pcenv:externalurl rdf:resource="external.xul"/>
        ...  </rdf:Description>
        ... </rdf:RDF>
        ... \"\"\"
        >>> uri = 'http://example.com/'
        >>> uri in input
        False
        >>> output = fix_pcenv_externalurl(input, uri)
        >>> uri + '/external.xul' in output
        False
    '''

    try:
        dom = etree.fromstring(xml)
    except etree.XMLSyntaxError:
        # silently aborting on parse errors.
        return xml

    externalurl = '{http://www.cellml.org/tools/pcenv/}externalurl'

    # RDF representation generated by PCEnv
    xulnodes = dom.xpath('.//rdf:Description[@pcenv:externalurl]',
        namespaces=CELLML_NSMAP)
    for node in xulnodes:
        xulname = node.xpath('string(@pcenv:externalurl)',
            namespaces=CELLML_NSMAP)
        if xulname:
            node.attrib[externalurl] = '/'.join([base, xulname])

    # Different form of RDF presentation
    xulnodes = dom.xpath('.//pcenv:externalurl',
        namespaces=CELLML_NSMAP)
    for node in xulnodes:
        xulname = node.text
        if xulname:
            node.text = '/'.join([base, xulname])

    # RDF representation generated by OpenCell
    xulnodes = dom.xpath('.//rdf:Description[@opencell:externalurl]',
        namespaces=CELLML_NSMAP)
    for node in xulnodes:
        xulname = node.xpath('string(@opencell:externalurl)',
            namespaces=CELLML_NSMAP)
        if xulname:
            node.attrib[externalurl] = '/'.join([base, xulname])

    # Different form of RDF presentation
    xulnodes = dom.xpath('.//opencell:externalurl',
        namespaces=CELLML_NSMAP)
    for node in xulnodes:
        xulname = node.text
        if xulname:
            node.text = '/'.join([base, xulname])

    result = etree.tostring(dom, encoding='utf-8', xml_declaration=True)
    return result
