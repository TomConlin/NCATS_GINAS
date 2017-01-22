import yaml
import json
import re
import logging

LOG = logging.getLogger(__name__)


# TODO will need to adapt to how they embed dates in releases
GINASURL = 'https://tripod.nih.gov/ginas/gsrs/fullSeedData-2016-06-16.gsrs'


files = {
    'f1': {
        'file': 'fullSeedData-2016-06-16_records.json',   # for testing
        'url': 'https://tripod.nih.gov/ginas/gsrs/fullSeedData-2016-06-16.gsrs'
    },
    'curie': {
        # Via Matt's spreadsheet
        # https://docs.google.com/spreadsheets
        # /d/1X46U8VChiBslOwcv8AtRgwMitgcrx2zw-61YdFHc3rs/edit#gid=994949323

        'file': 'ginas_curie.yaml'
    },
    'maps': {
        # zcat fullSeedData-2016-06-16.gsrs  | cut -f1,2  > ginas_unii_uuid.tab
        # note:
        # 5k of these will have the string 'ingredient' decorating the UNII
        #
        # zcat fullSeedData-2016-06-16.gsrs  | cut -f1,2 | \
        #     sed 's/WORKED: //g;s/\[ingredient\] /citation:/g'
        #     > ginas_unii_uuid.tab

        'unii_uuid': {
            'file': 'ginas_unii_uuid.tab'
        },
        'unii_inchikey': {
            # from biothing's Greg Stuppie
            'file': 'unii_inchikey.csv',
            'url': 'https://raw.githubusercontent.com/stuppie/ncats-ingest/master/ginas/map_to_mydrug/unii_inchikey.csv'
        }
    }
}

# note raw file includes but is not limited to json so can't just:
# ginas = requests.get(GINASURL).json()


    # def fetch():
    # wget --timestamping https://tripod.nih.gov/ginas/gsrs/fullSeedData-2016-06-16.gsrs
    # zcat fullSeedData-2016-06-16.gsrs | cut -f3 > fullSeedData-2016-06-16.json
    # or
    # curl GINASURL | zcat | cut -f3 > fullSeedData-2016-06-16.json
    #
    # Each row should be valid by itself, but all together they are not.
    #
    # resovoir_sample.awk -v K=10 fullSeedData-2016-06-16.json| \
    # awk 'BEGIN{print"{\"records\":["}{if(last)print last ",";last=$0}END{print last "]}"}'\
    # > fullSeedData-2016-06-16_sample.json


triples = []

CURIEMAP = yaml.load(files['curie']['file'])

line_count = 0
UUID_UNII = {}
with open(files['maps']['unii_uuid']['file']) as fh:
    for line in fh:
        line_count += 1
        try:
            (unii, tab, uuid) = line.partition('\t')
            UUID_UNII[uuid.strip()] = unii
        except ValueError:
            LOG.error(
                'UUID_UNII mapping file %s failed to parse at line %i have %s',
                files['maps']['unii_uuid']['file'], line_count, line)
            break

line_count = 0
UNII_INCHIKEY = {}
with open(files['maps']['unii_inchikey']['file']) as fh:
    for line in fh:
        line_count += 1
        try:
            (unii, comma, inchikey) = line.partition(',')
            UNII_INCHIKEY[unii] = inchikey
        except ValueError:
            LOG.error(
                'UNII_INCHIKEY file  %s failed to parse at line %i have %s',
                files['maps']['unii_inchikey']['file'], line_count, line)
            break


def make_spo(s, p, o):
    # s & p get decorated, o we decorate ourselves
    statement = '<' + s + '> <' + p + '> ' + o + ' .'
    triples.append(statement)


OUTPUT = open('./ginas.nt', 'w')

with open(files['f1']['file'], 'r') as fh:
    ginas = json.load(fh)


for record in ginas['records']:
    uuid = record['uuid']
    altkey = UUID_UNII[uuid]
    if 'approvalID' in record:
        unii = record['approvalID']
        pkey = 'UNII:' + unii
        if unii != altkey:
            LOG.warning(
                'outer UNII (%s) !=  inner UNII (%s) for record %s',
                altkey, unii, uuid)
    else:
        pkey = altkey
        # currently do not know where to link these to
        # but want to see if they end up being referenced by other records

    make_spo(pkey, 'GINAS:uuid', '"' + uuid + '"')
    if unii in UNII_INCHIKEY:
        make_spo(
            pkey, 'CHEBI:InChIKey', '"' + UNII_INCHIKEY[unii].strip() + '"')
    else:
        LOG.info('No InchiKey for %s', pkey)

    # Structure
    if 'structure' in record:
        structure = record['structure']

        for att in [
                'smiles', 'formula', 'opticalActivity', 'atropoisomerism',
                'stereoComments', 'stereoCenters', 'definedStereo',
                'ezCenters', 'charge', 'mwt']:

            if att in structure and structure[att] is not None\
                    and structure[att] != '':
                make_spo(
                    pkey, 'GINAS:structure_' + att,
                    '"' + str(structure[att]) + '"')

        # for ref in structure['references']:
        #    make_spo(
        #        pkey, 'GINAS:structure_references', '<GINASREF:' + ref + '>')

    # Mixture
    if 'mixture' in record:
        mixture = record['mixture']
        for component in mixture['components']:
            make_spo(
                pkey,
                'GINAS:mixture_component_type', '"' + component['type'] + '"')
            substance = component['substance']
            make_spo(
                pkey,
                'GINAS:mixture_component_substance',
                '<UNII:' + UUID_UNII[substance['refuuid']] + '>')

    # Moieties
    # if 'moieties' in record:
    #    for moiety in record['moieties']:
    ######################################

    #  "status": "approved",
    #  "approvedBy": "FDA_SRS",
    #  "deprecated": false,
    #  "approved": 1466087557792,      too big to be a unix timestamp

    make_spo(
        pkey, 'GINAS:substanceClass', '"' + record['substanceClass'] + '"')

    # Name
    for name in record['names']:
        if name["preferred"]:
            make_spo(pkey,   'rdfs:label', '"' + name['stdName'] + '"')

            # for ref in name['references']:
            #    make_spo(
            #        pkey, 'name_references', '<GINASREF:' + ref + '>')

    # Code
    for code in record['codes']:
        if 'type' in code and code["type"] == 'PRIMARY':
            # conflaing codeSystem:code  might not be the best idea
            make_spo(
                pkey,
                'GINAS:codes_code',
                '<' + code['codeSystem'] + ':' + code['code'] + '>')
            for ref in code['references']:
                make_spo(
                    pkey, 'GINAS:code_references', '<GINASREF:' + ref + '>')

    # Relationships
    for relationship in record['relationships']:
        if 'relatedSubstance' in relationship \
                and relationship['relatedSubstance'] is not None:
            relatedSubstance = relationship['relatedSubstance']
            # there are multiple paths to a relationship identifier
            fkey = related_unii = None
            if 'approvalID' in relatedSubstance \
                    and relatedSubstance['approvalID'] is not None:
                fkey = relatedSubstance['approvalID']
            else:
                LOG.warning('Related Substance for %s is missing a UNII', pkey)
            if 'refuuid' in relatedSubstance \
                    and relatedSubstance['refuuid'] is not None:
                related_unii = UUID_UNII[relatedSubstance['refuuid']]
                if fkey is None:
                    fkey = related_unii
            else:
                LOG.warning(
                    'Related Substance for %s is missing a UUID', pkey)
            if related_unii is None and fkey is None and related_unii != fkey:
                LOG.warning(
                    'Related Substance for %s contradicts %s v.s %s',
                    pkey, fkey, related_unii)
            if related_unii is None and fkey is None:
                LOG.warning('No related identifier for %s', pkey)
                continue

            pred = relationship['type']
            pred = re.sub(r'>', '-', pred)
            pred = re.sub(r' ', '_', pred)
            pred = re.sub(r'/', '_', pred)
            make_spo(
                pkey, 'GINAS:' + pred, '<UNII:' + fkey + '>')

    # References (get their own pk)
    for reference in record['references']:
        if reference["publicDomain"]:
            make_spo(
                pkey,
                'GINAS:reference_uuid', '<GINASREF:' + reference['uuid'] + '>')
            # many of these citations have empty xml tags:  <SRS_LEGACY_DATA>
            make_spo(
                'GINASREF:' + reference['uuid'],
                'GINAS:reference_citation', '"' + reference['citation'] + '"')
            # make_spo(
            #    'GINASREF:' + reference['uuid'],
            #    'GINAS:reference_docType',  '"' + reference['docType'] + '"')
            if 'url' in reference:   # 'GINAS:reference_url'
                make_spo(
                    'GINASREF:' + reference['uuid'],
                    'OIO:hasdbxref', '<' + reference['url'] + '>')

            # if 'tags' in reference:
            #   for tag in reference['tags']:
            #        make_spo(
            #            'GINASREF:' + reference['uuid'],
            #            'GINAS:reference_tag', '"' + tag + '"')

print('Statements: ' + str(len(triples)))
tripleset = set(triples)
triples = list(tripleset)
print('Distinct:   ' + str(len(triples)))
print('\n'.join(triples), file=OUTPUT)
OUTPUT.close()
