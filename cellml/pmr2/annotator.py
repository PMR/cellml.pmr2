from shutil import rmtree
from lxml import etree
import re
import tempfile
import os
import time
from os import listdir
from os.path import join, dirname, splitext
from cStringIO import StringIO
import cPickle as pickle

import zope.interface
import zope.component

from pmr2.app.factory import named_factory
from pmr2.app.annotation.interfaces import *
from pmr2.app.annotation.annotator import ExposureFileAnnotatorBase
from pmr2.app.annotation.annotator import PortalTransformAnnotatorBase
from pmr2.app.exposure.interfaces import IExposureSourceAdapter

from cellml.api.pmr2.interfaces import ICellMLAPIUtility
from cellml.api.simple import celeds

from cellml.pmr2.cmeta import Cmeta
from cellml.pmr2.interfaces import *

LANG_SOURCE = join(dirname(__file__), 'lang')
XSLT_SOURCE = join(dirname(__file__), 'xslt')
langpath = lambda x: join(LANG_SOURCE, x)
xsltpath = lambda x: join(XSLT_SOURCE, x)

mathmlc2p_xslt = etree.parse(xsltpath('mathmlc2p.xsl'))
re_date = re.compile('^[0-9]{4}(-[0-9]{2}){0,2}')


class PTCellML2MathMLAnnotator(PortalTransformAnnotatorBase):
    zope.interface.implements(IExposureFileAnnotator)
    transform = 'pmr2_processor_legacy_cellml2html_mathml'
    title = u'Basic MathML'
    label = u'Mathematics'
    description = u''
    for_interface = IRawTextNote

    def generate(self):
        return (
            ('text', self.convert(self.input).decode('utf8')),
        )

PTCellML2MathMLAnnotatorFactory = named_factory(PTCellML2MathMLAnnotator)


class CellMLMathAnnotator(ExposureFileAnnotatorBase):
    zope.interface.implements(IExposureFileAnnotator)
    title = u'CellML Math Extraction'
    label = u'Mathematics'
    description = u''
    for_interface = ICellMLMathNote

    def maths(self):
        # Since the CellML API's load model method does not support 
        # asynchronious operation, we must fork it so it doesn't block
        # the server from doing its job.
        # 
        # When Zope/Plone can run on Python 2.6, this can be ported to
        # use multiprocessing module.

        blocksize = 512
        chunks = []

        def __maths():
            # XXX Originally I assumed the Python bindings to the CellML API
            # could be ready, however this is not the case.  Please refer to
            # the installed version of cellml.api.pmr2 for what it really is
            # doing.
            cu = zope.component.getUtility(ICellMLAPIUtility)
            sa = zope.component.queryAdapter(
                self.context, IExposureSourceAdapter)
            exposure, workspace, path = sa.source()
            modelfile = '%s/@@%s/%s/%s' % (workspace.absolute_url(),
                'rawfile', exposure.commit_id, path)
            model = cu.loadModel(modelfile)
            results = cu.extractMaths(model)
            return results

        def readpipe(fd):
            while True:
                lump = os.read(fd, blocksize)
                if not lump:
                    break
                chunks.append(lump)

        def writepipe(fd, stream):
            while True:
                lump = stream.read(blocksize)
                if not lump:
                    break
                bytes = os.write(fd, lump)

        try:
            p = os.pipe()
        except:
            # might want to use a proper exception type, likewise below.
            raise Exception('failed to open pipe')

        child_pid = os.fork()
        if child_pid == -1:
            raise Exception('failed to spawn child for math extraction')

        if child_pid == 0:
            try:
                results = __maths()
                raw = pickle.dumps(results)
                cooked = StringIO(raw)
                writepipe(p[1], cooked)
            finally:
                os.close(p[0])
                os.close(p[1])
                os._exit(0)
        else:
            # read whatever child wrote, so we don't need to write
            os.close(p[1])
            pid = 0
            while not pid:
                # we might want a sane upper limit on maximum running 
                # time for the child.
                pid, status = os.waitpid(child_pid, os.WNOHANG)
                # need to empty the pipe.
                readpipe(p[0])
                time.sleep(0.01)
            try:
                blob = ''.join(chunks)
                results = blob and pickle.loads(blob) or []
            finally:
                os.close(p[0])

        return results

    def generate(self):
        def mathc2p(s):
            r = StringIO()
            t = etree.parse(StringIO(s))
            t.xslt(mathmlc2p_xslt).write(r)
            return r.getvalue()
        maths = self.maths()
        maths = [(k, [mathc2p(m) for m in v]) for k, v in maths]
        return (
            ('maths', maths),
        )

CellMLMathAnnotatorFactory = named_factory(CellMLMathAnnotator)


class CellML2CAnnotator(PortalTransformAnnotatorBase):
    zope.interface.implements(IExposureFileAnnotator)
    transform = 'pmr2_processor_cellmlapi_cellml2c'
    title = u'CellML C Code Generation'
    label = u'Procedural C Code'
    description = u''
    for_interface = IRawTextNote

    def generate(self):
        return (
            ('text', self.convert(self.input).decode('utf8')),
        )

CellML2CAnnotatorFactory = named_factory(CellML2CAnnotator)


class CellMLCodegenAnnotator(ExposureFileAnnotatorBase):
    zope.interface.implements(IExposureFileAnnotator)
    title = u'CellML Code Generation'
    label = u'Generated Code'
    description = u''
    for_interface = ICellMLCodegenNote

    def codegen(self):
        # Since the CellML API's load model method does not support 
        # asynchronious operation, we must fork it so it doesn't block
        # the server from doing its job.
        # 
        # Also, we fork here rather than per language, as I am assuming
        # the overhead of spawning a process per language outweighs the
        # cost of pickling/unpickling a list of tuples of strings.
        # 
        # When Zope/Plone can run on Python 2.6, this can be ported to
        # use multiprocessing module.

        blocksize = 512
        chunks = []

        def __codegen():
            sa = zope.component.queryAdapter(
                self.context, IExposureSourceAdapter)
            exposure, workspace, path = sa.source()
            modelfile = '%s/@@%s/%s/%s' % (workspace.absolute_url(),
                'rawfile', exposure.commit_id, path)
            # XXX should verify the permission of the workspace also.
            results = []
            fn = listdir(LANG_SOURCE)
            for f in fn:
                langfile = langpath(f)
                lang = splitext(f)[0]
                result = celeds(modelfile, langfile)
                results.append((lang, result,))
            return results

        def readpipe(fd):
            while True:
                lump = os.read(fd, blocksize)
                if not lump:
                    break
                chunks.append(lump)

        def writepipe(fd, stream):
            while True:
                lump = stream.read(blocksize)
                if not lump:
                    break
                bytes = os.write(fd, lump)

        try:
            p = os.pipe()
        except:
            # might want to use a proper exception type, likewise below.
            raise Exception('failed to open pipe')

        child_pid = os.fork()
        if child_pid == -1:
            raise Exception('failed to spawn child for code generation')

        if child_pid == 0:
            try:
                results = __codegen()
                raw = pickle.dumps(results)
                cooked = StringIO(raw)
                writepipe(p[1], cooked)
            finally:
                os.close(p[0])
                os.close(p[1])
                os._exit(0)
        else:
            # read whatever child wrote, so we don't need to write
            os.close(p[1])
            pid = 0
            while not pid:
                # we might want a sane upper limit on maximum running 
                # time for the child.
                pid, status = os.waitpid(child_pid, os.WNOHANG)
                # need to empty the pipe.
                readpipe(p[0])
                time.sleep(0.01)
            try:
                blob = ''.join(chunks)
                results = blob and pickle.loads(blob) or ()
            finally:
                os.close(p[0])

        return results

    def generate(self):
        return (
            ('code', dict(self.codegen())),
        )

CellMLCodegenAnnotatorFactory = named_factory(CellMLCodegenAnnotator)


class OpenCellSessionAnnotator(ExposureFileAnnotatorBase):
    zope.interface.implements(IExposureFileAnnotator, 
                              IExposureFileEditAnnotator)
    title = u'OpenCell Session Link'
    label = u'Simulate using OpenCell'
    for_interface = IOpenCellSessionNote

    def generate(self):
        return ()

OpenCellSessionAnnotatorFactory = named_factory(OpenCellSessionAnnotator)


class CmetaAnnotator(ExposureFileAnnotatorBase):
    zope.interface.implements(IExposureFileAnnotator)
    title = u'Basic CellML Metadata'
    label = u'Model Metadata'
    for_interface = ICmetaNote

    def generate(self):

        def generate_citation():
            ids = metadata.get_cmetaid()
            if not ids:
                # got no cmetaid, assuming no CellML metadata present.
                return

            citation = metadata.get_citation(ids[0])
            if not citation:
                # no citation, do nothing.
                return

            result['citation_id'] = citation[0]['citation_id']
            # more than just journal
            result['citation_bibliographicCitation'] = citation[0]['journal']
            result['citation_title'] = citation[0]['title']

            # XXX ad-hoc sanity checking
            issued = citation[0]['issued']
            if isinstance(issued, basestring) and re_date.search(issued):
                result['citation_issued'] = issued
            else:
                result['citation_issued'] = u''

            authors = []
            if not citation[0]['creator']:
                # no authors, we do not need the last field.
                return

            for c in citation[0]['creator']:
                family = c['family']
                given = c['given']
                if c['other']:
                    other = ' '.join(c['other'])
                else:
                    other = ''
                fn = (family, given, other)
                authors.append(fn)
                
            result['citation_authors'] = authors

        def generate_keywords():
            result['keywords'] = metadata.get_keywords()

        def generate_model_title():
            model_title = metadata.get_dc_title(node='')
            if model_title:
                result['model_title'] = model_title[0]

        def generate_model_authorship():
            dcvc = metadata.get_dc_vcard_info(node='')
            if not dcvc:
                return
            # using only first one
            info = dcvc[0]
            result['model_author'] = '%s %s' % (info['given'], info['family'])
            result['model_author_org'] = \
                '%s, %s' % (info['orgunit'], info['orgname']) 

        result = {}
        metadata = Cmeta(StringIO(self.input))

        generate_citation()
        generate_keywords()
        generate_model_title()
        generate_model_authorship()

        # annotators are expected to return a list of tuples.
        return result.items()

CmetaAnnotatorFactory = named_factory(CmetaAnnotator)
