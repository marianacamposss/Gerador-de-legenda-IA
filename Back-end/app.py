import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)
CORS(app)  # Habilita CORS para todas as rotas.

# Configura a API do Google Generative AI
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("A variável de ambiente GOOGLE_API_KEY não foi definida.")
    genai.configure(api_key=api_key)
except ValueError as e:
    print(f"Erro ao configurar a API do Google: {e}")
    # exit(1) # Descomente se quiser que o app pare se a chave não for encontrada

generation_config = {
    "temperature": 0.8, # Um pouco mais de criatividade
    "top_p": 0.9,
    "top_k": 40,      # Ajustado para dar mais opções ao modelo antes do top_p
    "max_output_tokens": 150, # Limite o tamanho da legenda, pode ajustar
}
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Tenta inicializar o modelo.
model = None
try:
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-latest", # Modelo atualizado
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    print("Modelo GenerativeModel inicializado com sucesso.")
except Exception as e:
    print(f"Erro ao inicializar o modelo GenerativeModel: {e}")

@app.route('/gerar_legenda', methods=['POST'])
def gerar_legenda_route():
    if model is None:
        return jsonify({"error": "O modelo de IA não foi inicializado corretamente. Verifique a configuração da API e os logs do servidor."}), 500

    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo de imagem enviado"}), 400
    
    file = request.files['file']
    keywords = request.form.getlist('keywords')

    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    if not keywords:
        # Considerar se quer permitir legendas sem palavras-chave ou retornar erro
        # return jsonify({"error": "Nenhuma palavra-chave fornecida"}), 400
        print("Nenhuma palavra-chave fornecida, gerando legenda apenas com base na imagem.")


    try:
        image_bytes = file.read()

        # ----- INÍCIO DA ALTERAÇÃO DO PROMPT -----
        prompt_text = "Crie uma legenda curta, criativa e única para esta imagem, com no máximo 3 frases.Não muito sensacionalista."
        if keywords:
            prompt_text += f" Use as seguintes palavras-chave como inspiração principal: {', '.join(keywords)}."
        
        # Instruções claras para a IA sobre o formato da saída:
        prompt_text += " Forneça APENAS o texto da legenda final. NÃO inclua frases introdutórias como 'Claro, aqui está...', 'Aqui estão algumas opções:', ou 'Legenda gerada:'. NÃO numere ou rotule as legendas como 'Opção 1', 'Opção 2', etc. NÃO peça para escolher uma opção. NÃO use formatação Markdown como asteriscos para negrito ou outros símbolos de formatação. Apenas o texto puro da legenda."
        # ----- FIM DA ALTERAÇÃO DO PROMPT -----
        
        print(f"Prompt enviado para a API: {prompt_text}") # Log do prompt

        contents = [
            prompt_text,
            {
                "mime_type": file.mimetype,
                "data": image_bytes
            }
        ]
        
        response = model.generate_content(contents)

        legenda = "Não foi possível gerar a legenda ou a resposta do modelo está vazia." # Default
        
        if response:
            try:
                # Tenta extrair o texto da resposta de forma mais robusta
                if response.candidates and \
                   response.candidates[0].content and \
                   response.candidates[0].content.parts:
                    
                    legenda_gerada = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text')).strip()
                    if legenda_gerada:
                        legenda = legenda_gerada
                    else:
                        # Fallback se parts estiverem vazias mas houver .text geral na resposta
                        if hasattr(response, 'text') and response.text and response.text.strip():
                            legenda = response.text.strip()
                        else: # Se parts estão vazias e não há .text, verificamos por bloqueio
                            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                                legenda = f"Legenda bloqueada. Motivo: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
                            else:
                                print(f"Resposta do modelo não continha texto extraível nas partes nem bloqueio: {response}")
                
                elif hasattr(response, 'text') and response.text and response.text.strip(): # Fallback se a estrutura de candidates não estiver presente
                     legenda = response.text.strip()
                
                elif hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason: # Se a resposta for diretamente um bloqueio
                     legenda = f"Legenda bloqueada. Motivo: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
                else:
                    print(f"Resposta inesperada do modelo (sem texto, candidates válidos ou bloqueio claro): {response}")


                # Se a legenda ainda contiver frases que pedimos para evitar, podemos tentar uma limpeza simples.
                # Esta é uma medida secundária, o prompt é o principal.
                # Executar apenas se não for uma mensagem de erro de bloqueio
                if not legenda.startswith("Legenda bloqueada"):
                    frases_indesejadas_inicio = [
                        "claro, aqui está uma legenda:", "claro, aqui está:", "aqui está sua legenda:", "aqui está:",
                        "legenda:", "opção 1:", "opção 2:", "opção 3:"
                    ]
                    # Removemos prefixos comuns de IA conversacional
                    legenda_lower_test = legenda.lower()
                    for frase in frases_indesejadas_inicio:
                        if legenda_lower_test.startswith(frase):
                            legenda = legenda[len(frase):].lstrip(": ").strip() # Limpa também ':' e espaços
                            legenda_lower_test = legenda.lower()
                            # Não precisa de break aqui, pode haver mais de uma "limpeza" necessária
                    
                    # Remover a frase final "Escolha a opção..." se ainda aparecer
                    frase_final_indesejada = "escolha a opção que melhor se adapta ao seu estilo e à mensagem que você deseja transmitir."
                    if legenda.lower().endswith(frase_final_indesejada):
                        legenda = legenda[:-(len(frase_final_indesejada))].strip()


            except AttributeError as e_attr:
                print(f"AttributeError ao processar resposta do modelo: {e_attr}. Resposta: {response}")
                if hasattr(response, 'text') and response.text:
                     legenda = response.text.strip() # Tenta pegar o texto bruto se a estrutura falhar
                # Verifica se foi bloqueio
                elif hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                    legenda = f"Legenda bloqueada. Motivo: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
                else:
                    legenda = "Erro ao processar a resposta do modelo (AttributeError)."
            except Exception as e_parse:
                print(f"Erro genérico ao extrair legenda da resposta: {e_parse}. Resposta: {response}")
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                    legenda = f"Legenda bloqueada. Motivo: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
                else:
                    legenda = "Erro ao extrair a legenda da resposta do modelo."
        
        print(f"Legenda gerada final: {legenda}") # Log da legenda final
        return jsonify({"legenda": legenda})

    except Exception as e:
        print(f"Erro durante a geração da legenda (nível superior): {e}")
        # Melhorar mensagens de erro para o cliente
        if "API key not valid" in str(e) or "API_KEY_INVALID" in str(e):
             return jsonify({"error": "Chave de API inválida ou não configurada corretamente. Verifique suas credenciais e a configuração do servidor."}), 500
        if "DeadlineExceeded" in str(e):
            return jsonify({"error": "A solicitação à API demorou muito para responder (timeout)."}), 504
        # Erros relacionados ao modelo não encontrado ou descontinuado
        if "404" in str(e) and ("model" in str(e).lower() or "deprecated" in str(e).lower()):
            return jsonify({"error": f"O modelo de IA especificado não foi encontrado ou foi descontinuado. Verifique a configuração do servidor. Detalhe: {str(e)}"}), 500
        # Erros de cota
        if "quota" in str(e).lower() or "ResourceExhausted" in str(e):
            return jsonify({"error": "Cota da API excedida. Por favor, verifique seus limites de uso na plataforma do Google AI."}), 429
        
        return jsonify({"error": f"Ocorreu um erro interno ao gerar a legenda. Tente novamente mais tarde."}), 500

if __name__ == '__main__':
    # Use a porta 5000 por padrão, mas pode ser alterada
    # Para produção, debug=False
    app.run(debug=True, port=5000)