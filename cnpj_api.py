#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan 17 11:40:22 2026

@author: rictom
https://github.com/rictom/cnpj-sqlite
https://github.com/rictom/cnpj_consulta
"""

import aiosqlite
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from typing import Optional
import os, sys, copy
#import base_cnpj

import sqlite3, pandas as pd, os, sys, signal, time, io, contextlib, webbrowser

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    os.chdir(application_path)
    print('application_path', application_path)
    
#-------------CNPJ SQLITE
import configparser, argparse, os, sys
config = configparser.ConfigParser()

confPadrao = 'cnpj_api.ini'
if (os.path.exists(confPadrao)):
    config.read(confPadrao, encoding='utf8')
else:
    print('O arquivo de configuracao ' + confPadrao + ' não foi localizado. Parando...')
    sys.exit(1)

#caminhoDBReceita = "cnpj.db" 
caminhoDBReceita = config['BASES'].get('base_cnpj').strip() 
PORTA_APP = config['ETC'].getint('porta')

if not os.path.exists(caminhoDBReceita):
    print(f'O arquivo {caminhoDBReceita} com a base de cnpjs em sqlite não foi encontrado. O arquivo deve ser gerado pelo script em https://github.com/rictom/cnpj-sqlite')
    sys.exit()

def ajustaVariaveis(): 
    global listaMunicipios, listaUFs, listaCnae, dictCnae, listaNatJur, dicSituacaoCadastral,listaSituacaoCadastral, dicPorteEmpresa, listaPorteEmpresa, data_referencia_base
    with contextlib.closing(sqlite3.connect(caminhoDBReceita)) as engine:
        listaMunicipios = sorted(pd.read_sql('''select descricao||" - "||codigo as mun from municipio''', engine, index_col=None ).mun.to_list())
        listaUFs =  ['AC', 'AL', 'AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO']
        listaCnae = sorted(pd.read_sql('''select codigo||"-"||descricao as cnae from cnae''', engine, index_col=None ).cnae.to_list())
        dictCnae = pd.read_sql('''select codigo, descricao from cnae''', engine, index_col=None ).set_index('codigo').T.to_dict('list')
        # dictCnae={'0111301': ['Cultivo de arroz'], '0111302': ['Cultivo de milho'], ...
        listaNatJur = sorted(pd.read_sql('''select codigo||"-"||descricao as natjur from natureza_juridica''', engine, index_col=None ).natjur.to_list())
        #listaSituacaoCadastral = ['01-Nula', '02-Ativa', '03-Suspensa', '04-Inapta', '08-Baixada']
        dicSituacaoCadastral = {'01':'Nula', '02':'Ativa', '03':'Suspensa', '04':'Inapta', '08':'Baixada'}
        listaSituacaoCadastral = [k +'-'+v for k,v in  dicSituacaoCadastral.items()]
        dicPorteEmpresa = {'00':'Não informado', '01':'Micro empresa', '03':'Empresa de pequeno porte', '05':'Demais (Médio ou Grande porte)'}
        listaPorteEmpresa =  [k +'-'+v for k,v in  dicPorteEmpresa.items()]
        #listaPorteEmpresa = ['00-Não informado', '01-Micro empresa', '03-Empresa de pequeno porte', '05-Demais (Médio ou Grande porte)']

        #cnpj_qtde = int(cur.execute("select valor from _referencia where referencia='cnpj_qtde'").fetchone()[0])  
        data_referencia_base = engine.execute("select valor from _referencia where referencia='CNPJ'").fetchone()[0]


ajustaVariaveis()

def verificaIndices():
    with contextlib.closing(sqlite3.connect(caminhoDBReceita)) as engine:
        sql = '''
             SELECT DISTINCT m.name as nome_tabela, ii.name as coluna_indexada
              FROM sqlite_master AS m,
                   pragma_index_list(m.name) AS il,
                   pragma_index_info(il.name) AS ii
             WHERE m.type = 'table' and m.name in ('empresas', 'estabelecimento')
         '''
        tabelas_colunas = set([k for k in engine.execute(sql).fetchall()])
        scolunas = set([k[1] for k in tabelas_colunas])
    dtabelas_colunasQueDevemEstarIndexadas = {'empresas':['natureza_juridica', 'porte_empresa', 'capital_social'],
                                               'estabelecimento':['uf', 'municipio', 'cnae_fiscal', 'situacao_cadastral', 'cep']}
    scolunasQueDevemEstarIndexadas = set(dtabelas_colunasQueDevemEstarIndexadas['empresas'] + dtabelas_colunasQueDevemEstarIndexadas['estabelecimento'])
    sdiff = scolunasQueDevemEstarIndexadas.difference((scolunas))
    if len(sdiff)==0:
        print('as colunas requeridas estão indexadas')
    else:
        lsql = []
        print('Faltam colunas para ser indexadas:', sdiff)
        print('A operação de criação de índices será realizada agora e pode levar horas... Aguarde!')
        for tabela, d in dtabelas_colunasQueDevemEstarIndexadas.items():
            for c in sdiff:
                if c in d:
                    sql = f'CREATE INDEX idx_{tabela}_{c} on {tabela}({c})'
                    print(sql)
                    lsql.append(sql)
        # r = input('Deseja indexar as colunas, isso levará dezenas de minutos ou até 1 hora?(y/n)')
        if 1: #r=='y':
            for sql in lsql:
                print(time.asctime(), 'Executando: ' + sql)
                with contextlib.closing(sqlite3.connect(caminhoDBReceita)) as engine, engine: # as engine,engine para fechar a conexão e dar commit
                    engine.execute(sql)
            print(time.asctime(), 'Fim da indexação')        
#.def verificaIndices

def verificaTabelas():
    sqlVerificaTabela = '''select name from sqlite_schema where type='table' '''
    with contextlib.closing(sqlite3.connect(caminhoDBReceita)) as engine: # as engine,engine para fechar a conexão e dar commit
        lista_tabelas = [k[0] for k in engine.execute(sqlVerificaTabela).fetchall()]
        print(lista_tabelas)

    sqlcnaes = '''
        CREATE TABLE cnaes_estabelecimentos AS
        WITH RECURSIVE split(cnpj, cnae_secundario, rest) AS (
           SELECT e.cnpj, '', e.cnae_fiscal_secundaria||',' FROM estabelecimento e
           UNION ALL SELECT
           cnpj,
           substr(rest, 0, instr(rest, ',')),
           substr(rest, instr(rest, ',')+1)
           FROM split WHERE rest!=''
        )
        SELECT cnpj, CAST(cnae_secundario as TEXT) as cnae, CAST('S' as TEXT) as tipo_cnae --S=secundário
        FROM split
        WHERE cnae_secundario!=''
        UNION ALL 
        SELECT e.cnpj, CAST(e.cnae_fiscal as TEXT) as cnae, CAST('P' as TEXT) as tipo_cnae from estabelecimento e --P=primário
        ;
        
        CREATE INDEX idx_cnaes_estabelecimentos_cnpj ON cnaes_estabelecimentos(cnpj);
        CREATE INDEX idx_cnaes_estabelecimentos_cnae ON cnaes_estabelecimentos(cnae);
        --CREATE INDEX idx_cnaes_estabelecimentos_tipo_cnae ON cnaes_estabelecimentos(tipo_cnae);
        '''
    if 'cnaes_estabelecimentos' not in lista_tabelas:
        print(time.asctime(), 'Criando tabela cnae secundária:')
        with contextlib.closing(sqlite3.connect(caminhoDBReceita)) as engine, engine: # as engine,engine para fechar a conexão e dar commit
            engine.executescript(sqlcnaes)
        print(time.asctime(), 'Criando tabela cnae secundária-fim')
    if 'tporte' not in lista_tabelas:
        print(time.asctime(), 'Criando tabela tporte:')
        with contextlib.closing(sqlite3.connect(caminhoDBReceita)) as engine, engine: # as engine,engine para fechar a conexão e dar commit
            sql = '''Create table tporte AS
                    SELECT  CAST('00' as TEXT) as codigo, CAST('Não informado' AS TEXT) as descricao
                    UNION
                    SELECT '01', 'Micro empresa'
                    UNION
                    SELECT '03', 'Empresa de pequeno porte'
                    UNION 
                    SELECT '05', 'Demais (Médio ou Grande porte)' 
                    '''                        
            engine.executescript(sql)
        print(time.asctime(), 'Criando tabela tporte-fim')        
    if 'tsituacao' not in lista_tabelas:
        print(time.asctime(), 'Criando tabela tsituacao:')
        
        with contextlib.closing(sqlite3.connect(caminhoDBReceita)) as engine, engine: # as engine,engine para fechar a conexão e dar commit
            sql = '''Create table tsituacao AS
                    SELECT CAST('01' AS TEXT) as codigo, CAST('Nula' AS TEXT) as descricao
                    UNION
                    SELECT '02', 'Ativa'
                    UNION
                    SELECT '03', 'Suspensa'
                    UNION
                    SELECT '04', 'Inapta'
                    UNION
                    SELECT '08', 'Baixada' 
                    '''    
            engine.executescript(sql)
        print(time.asctime(), 'Criando tabela tsituacao-fim')        
#.def verificaTabelaCnaes

def ajustaCnaes(cs):
    if not cs:
        return ''
    return ', '.join([i + '-' + dictCnae.get(i, [''])[0] for i in cs.split(',')])
    
def sqlWhereF(dados):
    cnpjin = dados['cnpj']
    cnpjin = cnpjin.replace('.','').replace('/','').replace('-','').replace(';',' ').replace(',',' ').strip()
    cnpjlista = [i.strip() for i in cnpjin.split(' ') if i.strip()]
    sqlwhere = ''
    if len(cnpjlista):
        #if '%' in cnpjin or
        if all(len(k)==8 for k in cnpjlista):
            #sqlwhere += ' WHERE ' + ' t.cnpj LIKE ? OR '*(len(cnpjlista)-1) + 't.cnpj LIKE ?'
            sqlwhere += ' WHERE te.cnpj_basico in (' + ' ?, '*(len(cnpjlista)-1) + '? )'
            inLista = [k[:8] for k in cnpjlista]
        else:
            sqlwhere += ' WHERE t.cnpj in (' + ' ?, '*(len(cnpjlista)-1) + '? )'
            inLista = cnpjlista
    else:
        inUF = dados['uf']
        inMunicipio = [k.split('-')[-1].strip() for k in dados['municipio']]
        inCEP = [k.strip() for k in  dados['cep'].replace('-','').split(' ') if k.strip()]
        inBairro = [k.strip() for k in  dados['bairro'].strip().split(';') if k.strip()]
        inNatJur = [k.split('-')[0].strip() for k in dados['natureza_juridica']]
        inCnae = [k.split('-')[0].strip() for k in dados['cnae_principal']]
        inSituacao = [k.split('-')[0].strip() for k in dados['situacao_cadastral']]
        inPorte = [k.split('-')[0].strip() for k in dados['porte']]
        inSimples = dados['simples']
        inMei = dados['mei']
        inLista = []
        
        for coluna in ['capital_social_menor', 'capital_social_maior', 'data_inicio_atividades_menor', 'data_inicio_atividades_maior']: #, (inSimples, 'ts.opcao_simples'), (inMei, 'ts.opcao_mei')]:
            valor = dados[coluna.split('.')[-1]]
            if valor:
                if sqlwhere: 
                    sqlwhere += ' AND '
                if coluna.endswith('_menor'): #coluna=='capital_social_menor':
                    sqlwhere += " " + coluna.removesuffix('_menor') + "<?"  #" capital_social < ?"
                elif coluna.endswith('_maior'): #coluna=='capital_social_maior':
                    sqlwhere += " " + coluna.removesuffix('_maior') + ">?" #+= " capital_social > ?"
                else:
                    sqlwhere += coluna + " = ?"
                #inLista += [valor,]        
                inLista.append(valor)  
        
        for lista, coluna in [(inUF, 't.UF'), (inMunicipio, 't.municipio'), (inNatJur, 'te.natureza_juridica'),
                              (inSituacao, 't.situacao_cadastral'), (inPorte, 'te.porte_empresa'), 
                              (inCEP, 't.cep'), 
                              (inBairro, 't.bairro'),
                              (inCnae, 't.cnae_fiscal'),
                              (inSimples, 'ts.opcao_simples'), (inMei, 'ts.opcao_mei')]:
            if lista:
                if sqlwhere: 
                    sqlwhere += ' AND '
                if coluna=='t.cnae_fiscal' and dados['bcnae_secundaria']:
                    coluna = 'cnaes_estabelecimentos.cnae'
                if coluna !='t.bairro':
                    sqlwhere += coluna + ' in (' + ' ?, '*(len(lista)-1) + '? ) '
                else:
                    if len(lista)==1:
                        sqlwhere += '(' + coluna + ' like ? ) '
                    else:
                        sqlwhere += '(' + ('( trim(t.bairro) like ? ) OR ') *(len(lista)-1) + ' (trim(t.bairro) like ? ) )'
                inLista += lista
        if sqlwhere:
            if inCnae and dados['bcnae_secundaria']:
                sqlwhere = ''' LEFT JOIN cnaes_estabelecimentos on cnaes_estabelecimentos.cnpj=t.cnpj WHERE ''' + sqlwhere
            else:
                sqlwhere = 'WHERE ' + sqlwhere
            if dados['bcelular']:
                sqlwhere += " AND (substr(trim(t.telefone1), 1,1) in ('6','7','8','9') or substr(trim(t.telefone2), 1,1) in ('6','7','8','9') or substr(trim(t.fax), 1,1) in ('6','7','8','9')) "
            sqlwhere += ' LIMIT ?'
            if dados['action']=='consulta':
                #sqllimit = ' LIMIT ' + str(dados['klimiteTela'])
                inLista.append(dados['klimiteTela'])
            elif dados['action']=='exporta':
                #sqllimit = ' LIMIT ' + str(dados['klimiteExcel'])
                inLista.append(dados['klimiteExcel'])
            elif dados['action']=='json':
                inLista.append(dados['limite'])
    return sqlwhere, inLista
#.def sqlWhereF

def sqlSociosF(inLista):
    querySocios = '''
        SELECT t.cnpj, te.razao_social, t.cnpj_cpf_socio, t.nome_socio, sq.descricao as cod_qualificacao, 
            t.data_entrada_sociedade, t.pais, tpais.descricao as pais_, t.representante_legal, t.nome_representante, t.qualificacao_representante_legal, sq2.descricao as qualificacao_representante_legal_, t.faixa_etaria
        --FROM estabelecimento tt       
        --left join socios t on tt.cnpj=t.cnpj
        FROM socios t 
        LEFT JOIN estabelecimento tt on tt.cnpj=t.cnpj
        LEFT JOIN empresas te on te.cnpj_basico=tt.cnpj_basico
        LEFT JOIN qualificacao_socio sq ON sq.codigo=t.qualificacao_socio
        LEFT JOIN qualificacao_socio sq2 ON sq2.codigo=t.qualificacao_representante_legal
        left join pais tpais on tpais.codigo=t.pais
        where 
    '''

    if len(inLista)==1:
        querySocios += 'tt.cnpj=?'
    else:
        querySocios += 'tt.cnpj in ('
        querySocios += ' ?, '*(len(inLista)-1) + '? )'
    querySocios+= ' ORDER BY tt.cnpj, t.nome_socio '
    return querySocios
#.def sqlSociosF

SQL_BASE = '''

    select  --te.*, t.*, 
    t.cnpj, te.razao_social, te.natureza_juridica||'-'||tnat.descricao as natureza_juridica, 
    te.qualificacao_responsavel||'-'||tq.descricao as qualificacao_responsavel, 
    te.porte_empresa||'-'||tporte.descricao as porte_empresa, te.ente_federativo_responsavel, te.capital_social, 
    IIF(t.matriz_filial='1', 'Matriz', 'Filial')  as matriz_filial, t.nome_fantasia, t.situacao_cadastral||'-'||tsituacao.descricao as situacao_cadastral, t.data_situacao_cadastral, 
    t.motivo_situacao_cadastral||'-'||tmot.descricao as motivo_situacao_cadastral, 
    t.data_inicio_atividades, t.tipo_logradouro, t.logradouro, t.numero, t.complemento, t.bairro, t.cep, t.uf, 
    tmun.descricao as municipio, t.municipio as municipio_codigo, t.ddd1, t.telefone1, t.ddd2, t.telefone2, t.ddd_fax, t.fax, t.correio_eletronico, t.situacao_especial, t.data_situacao_especial, 
    t.nome_cidade_exterior, t.pais||'-'||ifnull(tpa.descricao,'') as pais, -- tq.descricao as _qualificacao_responsavel
    IFNULL(ts.opcao_simples, '') as opcao_simples, IFNULL(ts.opcao_mei, '') as opcao_mei,
    t.cnae_fiscal, -- tc.descricao as cnae_fiscal_, 
    t.cnae_fiscal_secundaria
    from estabelecimento t 
    left join empresas te on te.cnpj_basico=t.cnpj_basico 
    left join natureza_juridica tnat on tnat.codigo=te.natureza_juridica
    left join motivo tmot on tmot.codigo=t.motivo_situacao_cadastral
    left join municipio tmun on tmun.codigo=t.municipio
    -- left join cnae tc on tc.codigo=t.cnae_fiscal
    left join pais tpa on tpa.codigo=t.pais
    left join qualificacao_socio tq on tq.codigo=te.qualificacao_responsavel
    left join simples ts on ts.cnpj_basico=te.cnpj_basico
    left join tporte on tporte.codigo=te.porte_empresa
    left join tsituacao on tsituacao.codigo=t.situacao_cadastral
    
''' #t.cnpj=:cnpjin

#-------------API   
app = FastAPI(title="API Consulta CNPJs") #,
#     description="This is a API to get CNPJ data.",
#     #openapi_url="/openapi.json",
#     favicon_url="/static/favicon.ico")

DB_NAME = caminhoDBReceita

@app.get("/codigos")
async def listar_codigos():
    """Retorna tabelas de códigos dos campos porte_empresa, situacao_cadastral, mei, simples, natureza_juridica, cnae e municipio. Para utilizar a opção consultar, utilize esses códigos como parâmetros."""
    return {
            'porte_empresa':listaPorteEmpresa, 
            'situacao_cadastral':listaSituacaoCadastral,
            'mei':['S','N'],
            'simples':['S','N'],
            'natureza_juridica':listaNatJur, 
            'cnae':listaCnae,
            'municipio':listaMunicipios
            }

@app.get("/consultar_amostra")
async def listar_amostra():
    """Retorna 100 registros da tabela empresas, exibindo cnpj_basico e razão social."""
    try:
        async with aiosqlite.connect(DB_NAME, uri=True) as db:
            db.row_factory = aiosqlite.Row
            #query = '''select * from empresas where rowid > (abs(random()) % (select (select max(rowid) from empresas)+1)) LIMIT 10;'''
            async with db.execute("SELECT * FROM empresas limit 100") as cursor:
                rows = await cursor.fetchall()
                # Converte as linhas para dicionários
                return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/cnpj_basico/{cnpj_basico}")
async def buscar_por_cnpj_basico(cnpj_basico: str,
                                 limite:int=100):
    """Lista empresa e filiais a partir do radical do cnpj (8 primeiros dígitos). Esta rotina precisa ser otimizada... Está muito lenta!!!"""
    return await consultar(cnpj=cnpj_basico, limite=limite)

@app.get("/cnpj/{cnpj}")
async def buscar_por_cnpj(cnpj: str):
    """Mostra os dados de 1 único cnpj. Os sócios somente são exibidos quando é fornecido o cnpj da matriz."""
    return await consultar(cnpj=cnpj, exibe_socios='S')

@app.get("/cnpj/{cnpj_antes_da_barra}/{cnpj_depois_da_barra}")
async def buscar_por_cnpj_barra(cnpj_antes_da_barra: str, cnpj_depois_da_barra:str):
    """Mostra os dados de 1 único cnpj. Nesta opção o cnpj pode ter barra, traços ou pontos"""
    return await consultar(cnpj=cnpj_antes_da_barra+cnpj_depois_da_barra, exibe_socios='S')


@app.get("/consultar")
#async def consultar(request:Request):
async def consultar(cnpj:str = '',
                    uf:str = '',
                    municipio:str = '',
                    cep:str = '',
                    bairro:str = '',
                    natureza_juridica:str = '',
                    cnae:str = '',
                    busca_cnae_secundaria:str = 'S',
                    situacao_cadastral:str = '',
                    porte: str = '',
                    simples: str = '',
                    mei: str = '',
                    data_inicio_atividades_menor: Optional[str] = None, 
                    data_inicio_atividades_maior: Optional[str] = None,
                    capital_social_menor: Optional[str] = None,
                    capital_social_maior: Optional[str] = None, 
                    bcelular: str = '', 
                    exibe_socios: str = '', 
                    limite: int = 100, 
                    ):
    """Retorna registros por parametros cnpj, uf, cep, etc. Se for informado um cnpj ou mais de um (separado por vírgulas), os outros parâmetros serão ignorados. 
    Exemplos: -Para consultar dois cnpjs (podem ter pontos,traços ou barras - Os cnpjs devem ser separados por vírgulas): http://127.0.0.1:8000/consultar?cnpj=cnpj1,cnpj2 
    -Para consultar os dados de um cnpj com os sócios: http://127.0.0.1:8000/consultar?cnpj=cnpj&exibe_socios=S
    -Para consultar 200 empresas em SP: http://127.0.0.1:8000/consultar?uf=sp&limite=200 
    -Para consultar 1000 empresas de pequeno porte, em SP, na capital, http://127.0.0.1:8000/consultar?uf=SP&municipio=7107&porte_empresa=2limite=1000
    -Se desejar buscar empresas apenas com o cnae principal, coloque busca_cnae_secundaria=N
    -Para consultar 150 empresas no RS com dois tipos de cnae: http://127.0.0.1:8000/consultar?uf=RS&cnae=0115600-Cultivo de soja,1011201-Frigorífico - abate de bovinos&limite=250
    -A consulta anterior dará o mesmo resultado que: http://127.0.0.1:8000/consultar?uf=RS&cnae=0115600,1011201&limite=250, o texto no código após o hífen será ignorado
    -Para visualizar os códigos de cnae, municipio, porte_empresa e situacao_cadastral, utilize a opção /codigos/
    
    """
    
    dados = {'cnpj': cnpj, 
             'uf': [x.upper() for x in uf.split(',')], 
             'municipio': [] if not municipio else [x.upper() for x in municipio.split(',')], 
             'cep': cep, 
             'bairro': bairro, 
             'natureza_juridica': [] if not natureza_juridica else [x.upper() for x in natureza_juridica.split(',')], 
             'cnae_principal': [] if not cnae else [x.upper() for x in cnae.split(',')], 
             'bcnae_secundaria': ['S'] if busca_cnae_secundaria.upper()!='S' else [], 
             'situacao_cadastral': [] if not situacao_cadastral else [x.upper() for x in situacao_cadastral.split(',')], 
             'porte': [] if not porte else [x.upper() for x in porte.split(',')], 
             'simples': simples, 
             'mei': mei, 
             'data_inicio_atividades_menor': '', 
             'data_inicio_atividades_maior': '', 
             'capital_social_menor': None, 
             'capital_social_maior': None, 
             'bcelular': bcelular, 
             #'bsocios': True if bsocios.upper() in ('S','1') else False, 
             'limite': limite, 
             'action':'json'}  
    bsocios = True if exibe_socios.upper() in ('S','1') else False
    setCNPJs = set()
    resultado = []
    dadosSocios = []
    try:
        # Abre a conexão de forma assíncrona
        async with aiosqlite.connect(DB_NAME, uri=True) as db:
            db.row_factory = aiosqlite.Row
            #dados = {'cnpj':cnpj, 'uf':uf, 'municipio':'', 'cep':''}
            sqlwhere, inLista = sqlWhereF(dados) 
            #print(sqlwhere)
            sql = SQL_BASE + sqlwhere
            #print(sql)
            #async with db.execute(sql,  (cnpj,)) as cursor:
            async with db.execute(sql,  inLista) as cursor:
                #rows = await cursor.fetchall()
                async for dx in cursor:
                    d = dict(dx)
                    d['cnae_fiscal'] = ajustaCnaes(d['cnae_fiscal'])
                    d['cnae_fiscal_secundaria'] = ajustaCnaes(d['cnae_fiscal_secundaria'])
                    resultado.append(d)
                    setCNPJs.add(d['cnpj'])             
                if not bsocios:
                    return resultado
                else:
                    if len(setCNPJs):
                        querySocios = sqlSociosF(setCNPJs)
                        async with db.execute(querySocios, tuple(setCNPJs)) as cursor:
                            rows = await cursor.fetchall()
                            # Converte as linhas para dicionários
                            for dx in rows:
                                d = dict(dx) 
                                dadosSocios.append(d)
                return {'empresas':resultado, 'socios':dadosSocios}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")   
#.def consulta

if __name__ == "__main__":
    verificaIndices()
    verificaTabelas()
    print(f'Para acessar a api, use o endereço http:127.0.0.1:{PORTA_APP}/docs')
    import uvicorn
    # Ao rodar com uvicorn, o loop de eventos assíncronos já é gerenciado
    uvicorn.run(app,  host="0.0.0.0", port=PORTA_APP)