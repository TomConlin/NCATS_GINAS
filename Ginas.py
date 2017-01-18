import json


triples = []


def make_spo(s, p, o):
    # if s is None or p is None or o is None:
    #    print(s)
    #    print(p)
    #    print(o)

    # s & p get decorated, o we decorate ourselves
    statement = '<' + s + '> <' + p + ':> ' + o + ' .'
    # if statement is not None:
    # print(statement)
    triples.append(statement)


OUTPUT = open('./ginas.nt', 'w')

with open('fullSeedData-2016-06-16.json', 'r') as fh:
    ginas = json.load(fh)

for rec in ginas:
    pkey = 'GINAS:' + rec['ginas']
    make_spo(pkey, 'unii', '<UNII:' + rec['unid'] + '>')

    # not sure what this flag will indicate, it is not 'mixture'
    if 'ingredient' in rec:
        make_spo(pkey, 'ingredient', '"true"')

    record = rec['record']

    # Structure
    if 'structure' in record:
        structure = record['structure']
        for ref in structure['references']:
            make_spo(
                pkey, 'structure_references', '<GINASREF:' + ref + '>')
            make_spo(
                pkey, 'structure_formula', '"' + structure['formula'] + '"')
        if 'substanceClass' in structure:
            make_spo(
                pkey,
                'structure_substanceClass',
                '"' + structure['substanceClass'] + '"')

    # Mixture
    if 'mixture' in record:
        mixture = record['mixture']
        for component in mixture['components']:
            make_spo(
                pkey,
                'mixture_component_type', '"' + component['type'] + '"')
            substance = component['substance']
            make_spo(
                pkey,
                'mixture_component_substance',
                '<GINAS:' + substance['refuuid'] + '>')

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
        pkey, 'substanceClass', '"' + record['substanceClass'] + '"')

    # Name
    for name in record['names']:
        if name["preferred"]:
            make_spo(pkey, 'names_stdName', '"' + name['stdName'] + '"')
            for ref in name['references']:
                make_spo(
                    pkey, 'name_references', '<GINASREF:' + ref + '>')
    # Code
    for code in record['codes']:
        if 'type' in code and code["type"] == 'PRIMARY':
            # conflaing codeSystem:code  might not be the best idea
            make_spo(
                pkey,
                'codes_code',
                '<' + code['codeSystem'] + ':' + code['code'] + '>')
            for ref in code['references']:
                make_spo(pkey, 'code_references', '<GINASREF:' + ref + '>')

    # References (get their own pk)
    for reference in record['references']:
        if reference["publicDomain"]:
            make_spo(
                pkey, 'reference_uuid', '<GINASREF:' + reference['uuid'] + '>')
            make_spo(
                'GINASREF:' + reference['uuid'],
                'reference_citation', '"' + reference['citation'] + '"')
            make_spo(
                'GINASREF:' + reference['uuid'],
                'reference_docType',  '"' + reference['docType'] + '"')
            if 'url' in reference:
                make_spo(
                    'GINASREF:' + reference['uuid'],
                    'reference_url', '<' + reference['url'] + '>')
            if 'tags' in reference:
                for tag in reference['tags']:
                    make_spo(
                        'GINASREF:' + reference['uuid'],
                        'reference_tag', '"' + tag + '"')

print('Statements: ' + str(len(triples)))
tripleset = set(triples)
triples = list(tripleset)
print('Statements: ' + str(len(triples)))
print('\n'.join(triples), file=OUTPUT)
OUTPUT.close()
