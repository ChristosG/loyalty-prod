# Loyalty Program Recommendation App

This project is a sophisticated, agnostic recommendation application for loyalty programs, architected as a modular, event-driven system. It provides personalized recommendations by understanding a user's spending habits and matching them with available loyalty offers, **all without the need for traditional model training.**

The system ingests user transactions, enriches business data via web scraping and a local LLM, and uses this information to power a smart recommendation engine and an interactive chatbot.

## AI & Language Models

The intelligence of this application is powered by two distinct, locally-hosted Large Language Models.

*   **Tag Generation:** [**DeepSeek-R1-Distill-Llama-8B**](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Llama-8B) is used to analyze scraped business data and generate relevant, descriptive tags for the recommendation engine.
*   **Chatbot:** [**Llama-Krikri-8B-Instruct**](https://huggingface.co/ilsp/Llama-Krikri-8B-Instruct) powers the conversational RAG chatbot. This model was specifically chosen as the project was originally developed for a Greek hackathon, where it proudly secured **2nd place** (AI Hackathon challenge - February 2025).


## Key Features

*   **Zero Training Required:** The system operates on-the-fly by ingesting user history and loyalty offers, eliminating the need for pre-trained ML models.
*   **Event-Driven Architecture:** Uses **Kafka** for asynchronous messaging and **Debezium** for Change Data Capture (CDC), creating a resilient and scalable data pipeline.
*   **Dynamic Business Tagging:** A `scraper` service (via Searxng or Tavily) gathers real-time business information, which is then processed by a local **TensorRT-LLM on a Triton Server** to generate relevant and descriptive tags.
*   **High-Performance Communication:** Leverages **Redis** and **gRPC** for efficient, low-latency communication between the main application and the `grpcbot` backend.
*   **Smart Recommendation Filtering:** The recommendation engine uses an RFA-inspired filtering approach. It cross-references the user's transaction history with the database of business tags to suggest the 4 best-matching companies for point redemption.
*   **Interactive Chatbot with Dedicated UI:** If the initial recommendations aren't suitable, a user can talk to a chatbot. The chatbot is built with **Next.js** allowing users to make natural language queries (e.g., "Any travel deals?"). It uses a RAG (Retrieval-Augmented Generation) pipeline to find relevant offers.

## Architecture & Components

The project is organized as a microservices-oriented system, orchestrated with Docker Compose. Each component has a distinct responsibility:

| Directory | Component | Purpose |
| :--- | :--- | :--- |
| `recommendation_backend` | Recommendation Backend | The core service that provides recommendation logic based on user transactions and generated tags. |
| `scraper` | Scraper Service | Handles web scraping using Searxng or Tavily to gather business details. |
| `kafka_consumer` | Kafka Consumer | Listens to Kafka topics to process events (like new transactions) and trigger downstream actions. |
| `full_context_llama` | LLM Service | Contains the configuration and models for the TensorRT-LLM/Triton Inference Server for tag generation. |
| `grpcbot` | gRPC Chatbot Server | The gRPC server that powers the chatbot's RAG capabilities and communicates with the UI. |
| `grpcbot/chatbot-ui` | Chatbot UI | A **Next.js with Typescript/Tailwind** user interface for users to interact with the chatbot. |
| `initdb` | Database Initialization | Contains SQL scripts to set up the initial PostgreSQL database schema. |
| `searxng-docker` | Searxng Instance | A self-hosted instance of the Searxng metasearch engine for scraping. |
| `transactions_data` | Data Ingestion | Dummy data of transactions and loyalty offers. |

## System Flow

1.  **Data Ingestion**: User transactions are added to the PostgreSQL database.
2.  **Event Capture**: Debezium captures the database insertion as an event and pushes it to a **Kafka** topic.
3.  **Event Processing**: The `kafka_consumer` service picks up the event.
4.  **Data Enrichment**: The consumer triggers the `scraper` service to find information on the business from the transaction.
5.  **AI Tagging**: The scraped text is sent to the **LLM service**, which returns a set of descriptive tags.
6.  **Recommendation**: The `recommendation_backend` can now use this enriched data to provide personalized recommendations.
7.  **Conversational Search**: The user can interact with the `chatbot-ui`, which sends requests to the `grpcbot` to query the database for offers using natural language.

## Getting Started

### Prerequisites

*   Docker and Docker Compose
*   An **NVIDIA GPU** with drivers installed on the host machine to run the LLM container. More details on grpcbot README.md.
*   An optional API key for [Tavily](https://tavily.com/) if you wish to use it as a search provider.

### Installation and Running the Application

The entire environment is orchestrated with Docker Compose. You must bring up three separate `docker-compose` configurations **in the correct order**. Run these commands from the root directory of the project.

**1. Start the Core Infrastructure**

This command launches Kafka, Redis, PostgreSQL, and other foundational services.

```bash
# From the root directory of the project
docker compose up -d
```

**2. Start the LLM Server**

Please read the following: https://github.com/ChristosG/loyalty-prod/blob/main/grpcbot/README.md
Can be easily adjusted to use an external API (like openAI, etc..) instead.

**3. Start the Main Application and Chatbot**

After completing the initialization on for the LLM server, by running the 
```bash
cd ./grpcbot
docker compose up -d
```
will also start the Chatbot ui, which can be found on http://localhost:3000
