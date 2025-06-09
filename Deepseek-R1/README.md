# Deepseek R1 -Llama 8b for tag generation

Build R1 engine similarly like: [https://github.com/ChristosG/loyalty-prod/blob/main/grpcbot/README.md](https://github.com/ChristosG/loyalty-prod/blob/main/grpcbot/README.md)

After successfully built run ./start_r1.sh .

I have 2 gpus Nvidia 4060 Ti 16GB and 3060 12GB.
The former is for the chatbot because it's faster and  more memory supports longer context for conversations with multiple users (batched).
The latter for the R1 which generates the tags based on the scrapped data. **Note** that each business tag generation will be run once since its saved on the db which means lower usage.
