import yaml
import json
#  import rdflib
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
            (unii, uuid) = line.split()
            UUID_UNII[uuid] = unii
        except ValueError:
            LOG.error('UUID_UNII mapping file  %s failed to paded at line %i have %s',
                files['maps']['unii_uuid']['file'], line_count, line)
            break



def make_spo(s, p, o):
    # s & p get decorated, o we decorate ourselves
    statement = '<' + s + '> <' + p + ':> ' + o + ' .'
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
            LOG.warning('outer UNII (%s) !=  inner UNII (%s) for record %s',
            aktkey, unii, uuid)
    else:
        pkey = altkey
        # currently do not know where to link these
        # but want to see if they end up being reference by other records

    make_spo(pkey, 'GINAS:uuid', '"' + uuid + '"')

    # Structure
    if 'structure' in record:
        structure = record['structure']
        for ref in structure['references']:
            make_spo(
                pkey, 'GINAS:structure_references', '<GINASREF:' + ref + '>')
            make_spo(
                pkey,
                'GINAS:structure_formula', '"' + structure['formula'] + '"')
        if 'substanceClass' in structure:
            make_spo(
                pkey,
                'GINAS:structure_substanceClass',
                '"' + structure['substanceClass'] + '"')

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
    # if 'moieties' in rec:
    #    for moiety in moieties:
    ####################################

    #  "approvalID": "6V3I57K9UL",  already have as UNII
    #  "status": "approved",
    #  "approvedBy": "FDA_SRS",
    #  "deprecated": false,
    #  "approved": 1466087557792,      too big to be a unix timestamp

    #  "substanceClass": "chemical",
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

    # References (get their own pk)
    for reference in record['references']:
        if reference["publicDomain"]:
            make_spo(
                pkey,
                'GINAS:reference_uuid', '<GINASREF:' + reference['uuid'] + '>')
            make_spo(
                'GINASREF:' + reference['uuid'],
                'GINAS:reference_citation', '"' + reference['citation'] + '"')
            make_spo(
                'GINASREF:' + reference['uuid'],
                'GINAS:reference_docType',  '"' + reference['docType'] + '"')
            if 'url' in reference:
                make_spo(
                    'GINASREF:' + reference['uuid'],
                    'GINAS:reference_url', '<' + reference['url'] + '>')
            if 'tags' in reference:
                for tag in reference['tags']:
                    make_spo(
                        'GINASREF:' + reference['uuid'],
                        'GINAS:reference_tag', '"' + tag + '"')

print('Statements: ' + str(len(triples)))
tripleset = set(triples)
triples = list(tripleset)
print('Distinct:   ' + str(len(triples)))
print('\n'.join(triples), file=OUTPUT)
OUTPUT.close()
