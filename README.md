# cnpj_api
Api em python para consultar dados de empresas com dados abertos públicos da Receita Federal, utilizando uma base local em sqlite <b>cnpj.db</b>, que deve ser gerada utilizando o projeto https://github.com/rictom/cnpj-sqlite ou pelo programa <b>Rede_Cria_Tabelas</b>.

## Dados públicos de CNPJs no site da Receita:
Os arquivos csv zipados com os dados de CNPJs estão disponíveis em https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj ou https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/<br>

## Requisitos
Como a base ocupa bastante espaço, é recomendável ter 100GB de SSD disponível como disco principal no computador, bem como 16GB de memória RAM.

## Versão Executável
Uma versão executável está na pasta <b>apps</b> deste repositório. Foi gerado pela biblioteca pyinstaller e testado em Windows 10. Para gerar o arquivo cnpj.db (base de dados de empresas), baixe o programa <b>Rede_Cria_Tabelas</b> disponível em [https://www.redecnpj.com.br/rede/pag/aplicativo.html](https://www.redecnpj.com.br/rede/pag/aplicativo.html#rede_programa_baixar) e execute as partes 1 e 2 desse programa (baixar as bases e gerar a base cnpj.db). Descompacte o arquivo <b>cnpj_api.win.zip</b> e salve o arquivo <b>cnpj.db</b> na mesma pasta que <b>cnpj_api.exe</b>. Para executar, clique duas vezes no .exe.


## Versão Python
É recomendável criar um ambiente para rodar o projeto, siga as orientações em https://docs.python.org/pt-br/3/library/venv.html. O arquivo cnpj.db deve estar na mesma pasta que o script cnpj_listas.py. 

No console, dentro de um ambiente python, para instalar as bibliotecas utilizadas, rode
<b>pip install -r requirements_cnpj_api.txt</b>

Para executar o script para gerar listas, digite

<b>python cnpj_apis.py</b>

A primeira vez que o script for rodado, irá gerar índices no arquivo cnpj.db. Isso poderá levar dezenas de minutos ou horas para execução, dependendo do computador. O arquivo cnpj.db final terá mais de 60GB!

Abra o endereço http:127.0.0.1:8015/docs no navegador para visualizar a página de testes da api:
<img width="1436" height="575" alt="image" src="https://github.com/user-attachments/assets/3c33c15a-d99b-45a1-af8e-67372e366913" />



## Consulta por CNPJ(s)
A consulta de um cnpj, por exemplo, do Banco do Brasil, pode ser feita com a url<br>
http://127.0.0.1:8015/cnpj/00000000000191<br>
<img width="858" height="979" alt="image" src="https://github.com/user-attachments/assets/8edd47bf-097e-4147-8f07-0bc8cdff05ec" />


Podem ser colocados vários CNPJs separados por vírgulas ou ponto-e-vírgulas(;).
## Consulta por parâmetros (opção /consultar?)
As consultas podem ser feitas por UF, Município, CEP, Natureza Jurídica, CNAE primária ou secundária, Situação Cadastral, Porte da Empresa, Opção Simples, Opção Mei, Data de Início de Atividades e Capital Social.

Exemplos: 
- Para consultar dois cnpjs (podem ter pontos,traços ou barras - Os cnpjs devem ser separados por vírgulas): http://127.0.0.1:8000/consultar?cnpj=<cnpj 1>,<cnpj 2> onde <cnpj 1> e <cnpj 2> são dois CNPJs de empresas;<br>
- Para consultar os dados de um cnpj com os sócios: http://127.0.0.1:8000/consultar?cnpj=CNPJ_PROCURADO&exibe_socios=S<br>
- Para consultar 200 empresas em SP: http://127.0.0.1:8000/consultar?uf=sp&limite=200 <br>
- Para consultar 1000 empresas de pequeno porte, em SP, na capital, http://127.0.0.1:8000/consultar?uf=SP&municipio=7107&porte_empresa=2limite=1000<br>
- Se desejar buscar empresas apenas com o cnae principal, coloque busca_cnae_secundaria=N<br>
- Para consultar 250 empresas no RS com dois tipos de cnae: http://127.0.0.1:8000/consultar?uf=RS&cnae=0115600-Cultivo_de_soja,1011201-Frigorífico-abate_de_bovinos&limite=250<br>
- A consulta anterior dará o mesmo resultado que: http://127.0.0.1:8000/consultar?uf=RS&cnae=0115600,1011201&limite=250, o texto no código após o hífen será ignorado<br>
- Para visualizar os códigos de cnae, municipio, porte_empresa e situacao_cadastral, utilize a opção /codigos/<br>

Lembre-se que a base tem mais de 60 milhões de empresas, então dependendo dos parâmetros as consultas poderão demorar.

## Pré-requisitos:
Python 3.12;<br>
Bibliotecas fastAPI e aiosqlite.<br>

## DOE!:
Se o projeto for útil, faça uma doação para a Paróquia do Padre Júlio Lancelotti:
https://www.oarcanjo.net/site/doe/

## Dificuldades:
Em caso de erros, dúvidas ou sugestões, abra uma issue (https://github.com/rictom/cnpj_API/issues) neste repositório.

## Outras referências:
Projeto para visualizar os relacionamentos de sócios e de empresas de forma gráfica: https://github.com/rictom/rede-cnpj;<br>
Carregar os dados de cnpjs para o banco de dados MYSQL: https://github.com/rictom/cnpj-mysql.<br>

## Histórico de versões
versão 0.1 (janeiro/2026)
