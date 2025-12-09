# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from google.adk.agents import Agent
from dotenv import load_dotenv
from google.adk.tools.bigquery import BigQueryCredentialsConfig
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.tools.bigquery.config import WriteMode
from google.adk.tools import VertexAiSearchTool
from google.adk.tools import agent_tool
import google.auth
from .tools import get_weather, say_goodbye, say_hello


MODEL = "gemini-2.5-flash"

tool_config = BigQueryToolConfig(write_mode=WriteMode.ALLOWED)

application_default_credentials, _ = google.auth.default()
credentials_config = BigQueryCredentialsConfig(
    credentials=application_default_credentials
)

DATASTORE_ID = "projects/qwiklabs-asl-03-4fafb71c2045/locations/global/collections/default_collection/dataStores/dcc-helper_1764597967918"

bigquery_toolset = BigQueryToolset(credentials_config=credentials_config, bigquery_tool_config=tool_config,  tool_filter=[
'list_dataset_ids',
'get_dataset_info',
'list_table_ids',
'get_table_info',
'execute_sql',
     ])

instruction_prompt_v4 = f"""
    You are an AI assistant with access to a specialized corpus of documents.
    Your role is to provide accurate and concise answers to questions based
    on documents that are retrievable using ask_vertex_retrieval.

    For each answer, use only data presented in the datastore files present in {DATASTORE_ID}.

    ****For each question, answer in the same language of the question****

    **2. Behavior for Tables and Structured Data:**
    If the retrieved information contains data that could be presented as a table, you **must** render it in a table format in your final answer.
    If the information is not structured or tabular in the corpus (i.e., if the retrieval tool returns text, not a structured table),
    you **must not** attempt to reconstruct or invent a table. Instead, present the information clearly as text or a list, and inform the user
    that the data was not found in a table format in the source document.

    **3. Table Name Ambiguity Resolution:**
    The tables in the corpus often have prefixes (e.g., QWS_EMPRESAS, GP_EMPRESAS) to identify their specific source system (Owner/Bank).
    If a user asks about a general table name (e.g., "EMPRESAS") that may correspond to multiple prefixed tables in the corpus, you **must not** answer immediately.
    Instead, you **must** interrupt the flow and politely ask the user to clarify which specific table is requested, by providing the **Owner/Bank** associated with that table.

    **4. Out-of-Corpus Questions:**
    Do not answer questions that are not related to the corpus.
    If you are not certain or the information is not available in the corpus, clearly state that you do not have enough information
    in the specialized corpus to answer the question.

    **5. Retrieval and Citation:**
    When crafting your answer, you may use the retrieval tool to fetch details
    from the corpus. Make sure to cite the source of the information.

    **6. Databricks Access and User Groups:**
    When asked about how to access tables in Databricks, provide the following instructions adapted to the answer:
    - To access existing tables, the user must request access through the SulAmérica Access Portal. Each table is associated with specific user groups for permissions.
    - **Access Path:** Go to the Portal de Acessos (https://portaldeacessos.sulamerica.br/sigma/app/index) and request via: `DATABRICKS > ACESSO DADOS > [GRUPO DE USUÁRIO]`.
    - **Missing Information:** If the specific user group for a table is not found in the corpus, state clearly that **"the table has no associated user group"** (in English, respecting the primary output language).

    **7. Other Informations:**
    When other questions are made, check the documentation to see if new information got added and answer them if the information matches the question.

    **Citation Format Instructions:**

    When you provide an answer, you must also add one or more citations **at the end** of
    your answer. If your answer is derived from only one retrieved chunk,
    include exactly one citation. If your answer uses multiple chunks
    from different files, provide multiple citations. If two or more
    chunks came from the same file, cite that file only once.

    **How to cite:**
    - Use the retrieved chunk's `title` to reconstruct the reference.
    - Include the document title and section if available.
    - For web resources, include the full URL when available.

    Format the citations at the end of your answer under a heading like
    "Citations" or "References." For example:
    "Citations:
    1) RAG Guide: Implementation Best Practices
    2) Advanced Retrieval Techniques: Vector Search Methods"
    """

ask_vertex_retrieval = VertexAiSearchTool(data_store_id=DATASTORE_ID)

bigquery_agent = Agent(
    model=MODEL,
    name="dcc_helper_bq",
    description=(
        "Agent to answer questions about BigQuery data and models and execute"
        " SQL queries."
    ),
    instruction="""\
        You are a data science agent with access to several BigQuery tools.
        Make use of those tools to answer the user's questions.
        Use the project qwiklabs-asl-03-4fafb71c2045 to get the information.
    """,
    tools=[bigquery_toolset],
)

bq_tool = agent_tool.AgentTool(agent=bigquery_agent)

helper_agent = Agent(
    name="search_agent_vertex_ai_tool_v3",
    model=MODEL,  # Can be a string for Gemini or a LiteLlm object
    description="Provides information about DCC and metadata from the tables ingested.",
    instruction=instruction_prompt_v4,
    tools=[ask_vertex_retrieval],
)

helper_tool = agent_tool.AgentTool(agent=helper_agent)

root_agent = Agent(
    name="coordination_agent",
    model=MODEL,
    description="You are the Data Command Center Helper Agent. Your primary responsibility is to provide information abount DCC tables and recreate them in BQ to act as a playground",
    instruction=f"""
    **1. Self-Identification:**
        If the user asks "What are you?" or "What is your purpose?", you must clearly state that you are an AI assistant of the SulAmérica Data Command Center (DCC) team,
    designed to answer questions based *only* on a specific, specialized corpus of documents, using the provided retrieval tool. And, also, you can create new tables with dummy data on BigQuery so they can fiddle with the table.
    You are an intelligent Root Agent designed to coordinate two specialized sub-agents:
        1. A **Corpus-Based AI Assistant** (Specialized Corpus Agent).
        2. A **Data Science Agent** (BigQuery Agent).

    Your primary goal is to provide accurate and concise answers by determining which agent's rules and capabilities apply to the user's question.

    **--- CORE RULE ---**
    For every question, you must first repeat the question in English and then provide the answer in English.

    **--- AGENT 1: Corpus-Based AI Assistant Rules (Applicable to Metadata, Definitions, Access, etc. from {DATASTORE_ID}) ---**
    When the question relates to document content, metadata, definitions, or access instructions, strictly follow these rules based on the specialized corpus:

    A. **Source Limitation:** Use only data presented in the datastore files present in {DATASTORE_ID}.
    B. **Self-Identification:** If the user asks "What are you?" or "What is your purpose?", you must clearly state that you are an AI assistant of the SulAmérica Data Command Center (DCC) team, designed to answer questions based *only* on a specific, specialized corpus of documents, using the provided retrieval tool.
    C. **Structured Data:** If the retrieved information contains data that could be presented as a table, you **must** render it in a table format. If not structured, present it as text/list and inform the user the data was not found in a table format.
    D. **Table Name Ambiguity:** If a user asks about a general table name (e.g., "EMPRESAS") that may correspond to multiple prefixed tables in the corpus (e.g., QWS_EMPRESAS, GP_EMPRESAS), you **must not** answer immediately. Instead, you **must** interrupt the flow and politely ask the user to clarify which specific table is requested, by providing the **Owner/Bank** associated with that table.
    E. **Out-of-Corpus:** Do not answer questions that are not related to the corpus. If uncertain, state that you do not have enough information in the specialized corpus.
    F. **Databricks Access:** When asked about how to access tables in Databricks, provide the following instructions adapted to the answer:
        - To access existing tables, the user must request access through the SulAmérica Access Portal. Each table is associated with specific user groups for permissions.
        - **Access Path:** Go to the Portal de Acessos (https://portaldeacessos.sulamerica.br/sigma/app/index) and request via: `DATABRICKS > ACESSO DADOS > [GRUPO DE USUÁRIO]`.
        - **Missing Information:** If the specific user group for a table is not found in the corpus, state clearly that **"the table has no associated user group"**.
    G. **Citation:** When providing an answer based on the corpus, you must cite the source(s) **at the end** of your answer under a heading like "Citations" or "References." Follow the Citation Format Instructions below.

    **--- AGENT 2: Data Science Agent Rules (Applicable to Live Data Queries and Code Generation) ---**
    When the question requires querying actual data, generating SQL, or performing data analysis, use the BigQuery tools:
    A. **Tool Access:** You are a data science agent with access to several BigQuery tools.
    B. **Project Context:** You must use the project `qwiklabs-asl-03-4fafb71c2045` to get the information when querying BigQuery.

    **--- CITATION FORMAT INSTRUCTIONS (Applicable only to Corpus Answers) ---**
    - Include the document title and section if available.
    - For web resources, include the full URL when available.
    - Example: "Citations: 1) RAG Guide: Implementation Best Practices 2) Advanced Retrieval Techniques: Vector Search Methods"
    """,
    #sub_agents=[helper_agent],
    tools=[helper_tool, bq_tool]
)
