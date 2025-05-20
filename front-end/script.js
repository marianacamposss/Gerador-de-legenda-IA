document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('form-upload');
    const fileInput = document.getElementById('file');
    const chooseFileLabel = document.getElementById('choose-file-label');
    const fileNameDisplay = document.getElementById('file-name-display');
    const mensagemDiv = document.getElementById('mensagem');
    const listaImagens = document.getElementById('lista-imagens');
    const keywordsContainer = document.getElementById('keywords-container');
    const addKeywordBtn = document.getElementById('add-keyword-btn');
    const historicoTitulo = document.getElementById('historico-titulo');

    async function enviarParaBackend(file, keywords) {
        const formData = new FormData();
        formData.append('file', file);
        keywords.forEach(keyword => {
            formData.append('keywords', keyword);
        });

        mensagemDiv.innerHTML = `<p class="text-blue-600">Enviando imagem e gerando legenda... Por favor, aguarde.</p>`;
        mensagemDiv.classList.remove('hidden');

        try {
            const response = await fetch('http://localhost:5000/gerar_legenda', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                let errorMsg = `Erro HTTP: ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.error || errorData.message || errorMsg;
                } catch (e) {
                    const textError = await response.text();
                    if (textError) errorMsg = textError;
                }
                throw new Error(errorMsg);
            }

            const data = await response.json();
            if (data.error) {
                throw new Error(data.error);
            }
            return data.legenda;
        } catch (error) {
            console.error("Erro ao chamar o backend:", error);
            if (error.message === 'Failed to fetch') {
                 throw new Error('Não foi possível conectar ao servidor. Verifique se ele está rodando e a URL está correta.');
            }
            throw error;
        }
    }

    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        const file = fileInput.files[0];
        const keywordInputs = keywordsContainer.querySelectorAll('.keyword-input');
        const keywords = [];
        keywordInputs.forEach(input => {
            if (input.value.trim() !== '') {
                keywords.push(input.value.trim());
            }
        });

        if (!file) {
            mensagemDiv.innerHTML = `<p class="text-red-500">Por favor, selecione uma imagem antes de enviar.</p>`;
            mensagemDiv.classList.remove('hidden');
            fileNameDisplay.textContent = 'Nenhum arquivo selecionado';
            return;
        }
        if (keywords.length === 0) {
            mensagemDiv.innerHTML = `<p class="text-red-500">Por favor, adicione pelo menos uma palavra-chave para gerar a legenda.</p>`;
            mensagemDiv.classList.remove('hidden');
            return;
        }

        try {
            const legendaGerada = await enviarParaBackend(file, keywords);
            const reader = new FileReader();
            reader.onload = function () {
                const imagemURL = reader.result;
                const li = document.createElement('li');
                li.classList.add('bg-gray-100', 'p-4', 'rounded-lg', 'shadow-md', 'flex', 'flex-col', 'items-center', 'md:flex-row', 'md:items-start', 'gap-4');

                let cleanedLegenda = legendaGerada;
                const prefixesToRemove = [
                    "claro, aqui está uma legenda:", "claro, aqui está:", "aqui está sua legenda:",
                    "aqui está:", "legenda:", "opção 1:", "opção 2:", "opção 3:"
                ];
                for (const prefix of prefixesToRemove) {
                    if (cleanedLegenda.toLowerCase().startsWith(prefix)) {
                        cleanedLegenda = cleanedLegenda.substring(prefix.length).trim();
                        break;
                    }
                }

                const legendaId = `legenda-${Date.now()}`;

                // MODIFICAÇÃO INÍCIO: Adicionar botão de excluir e agrupar botões
                li.innerHTML = `
                  <img src="${imagemURL}" alt="Imagem enviada" class="max-w-[150px] md:max-w-[200px] h-auto rounded-md object-contain">
                  <div class="text-center md:text-left flex-grow">
                    <p class="font-semibold text-gray-700 mb-1">Legenda Gerada:</p>
                    <p class="text-gray-800 break-words" id="${legendaId}">${cleanedLegenda}</p>
                    <div class="flex items-center space-x-2 mt-2 justify-center md:justify-start">
                        <button class="copy-caption-btn bg-[#ed6a5a] hover:bg-[#e4998f] text-white font-semibold py-1 px-3 rounded-md text-sm" data-caption-text="${cleanedLegenda.replace(/"/g, '"')}">
                          Copiar Legenda
                        </button>
                        <button class="delete-caption-btn bg-gray-400 hover:bg-gray-500 text-white font-semibold py-1 px-3 rounded-md text-sm">
                          Excluir
                        </button>
                    </div>
                  </div>
                `;
                // MODIFICAÇÃO FIM: Adicionar botão de excluir e agrupar botões

                if (listaImagens.firstChild) {
                    listaImagens.insertBefore(li, listaImagens.firstChild);
                } else {
                    listaImagens.appendChild(li);
                }
                historicoTitulo.style.display = 'block';
                mensagemDiv.innerHTML = `<p class="text-green-600">Legenda gerada com sucesso para <strong>${file.name}</strong>!</p>`;
                form.reset();
                fileNameDisplay.textContent = 'Nenhum arquivo selecionado';
                const keywordRows = keywordsContainer.querySelectorAll('.keyword-row');
                keywordRows.forEach((row, index) => {
                    const input = row.querySelector('.keyword-input');
                    if (input) input.value = '';
                });
            };
            reader.readAsDataURL(file);
        } catch (error) {
            mensagemDiv.innerHTML = `<p class="text-red-500">Erro ao gerar a legenda: ${error.message}</p>`;
            mensagemDiv.classList.remove('hidden');
        }
    });

    function criarKeywordRow() {
        const newKeywordRow = document.createElement('div');
        newKeywordRow.classList.add('keyword-row', 'flex', 'items-center', 'space-x-2', 'mb-2');
        newKeywordRow.innerHTML = `
          <input type="text" class="keyword-input p-3 border border-[#9bc1bc] rounded-xl w-full focus:outline-none focus:ring-2 focus:ring-[#9bc1bc] text-sm placeholder-gray-400" placeholder="Nova palavra-chave...">
          <button type="button" class="remove-btn bg-[#ed6a5a] hover:bg-[#e4998f] text-white font-semibold py-2 px-3 rounded-xl text-sm flex-shrink-0">Remover</button>
        `;
        keywordsContainer.appendChild(newKeywordRow);

        const removeBtn = newKeywordRow.querySelector('.remove-btn');
        removeBtn.addEventListener('click', function () {
            newKeywordRow.remove();
        });
        newKeywordRow.querySelector('.keyword-input').focus();
    }

    addKeywordBtn.addEventListener('click', criarKeywordRow);

    keywordsContainer.querySelectorAll('.keyword-row .remove-btn').forEach(button => {
        button.addEventListener('click', function () {
            button.closest('.keyword-row').remove();
        });
    });

    fileInput.addEventListener('change', function() {
        if (this.files && this.files.length > 0) {
            fileNameDisplay.textContent = this.files[0].name;
        } else {
            fileNameDisplay.textContent = 'Nenhum arquivo selecionado';
        }
        mensagemDiv.classList.add('hidden');
    });

    // Event listener delegado para os botões de copiar e excluir
    listaImagens.addEventListener('click', function(event) {
        const target = event.target;

        // Lógica para o botão Copiar
        if (target.classList.contains('copy-caption-btn')) {
            const button = target;
            const textToCopy = button.dataset.captionText;

            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(textToCopy).then(() => {
                    const originalText = button.textContent;
                    button.textContent = 'Copiado!';
                    button.disabled = true;
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.disabled = false;
                    }, 2000);
                }).catch(err => {
                    console.warn('Erro ao copiar para a área de transferência:', err);
                    alert('Não foi possível copiar a legenda. Tente manualmente.');
                });
            } else {
                try {
                    const textArea = document.createElement("textarea");
                    textArea.value = textToCopy;
                    textArea.style.position = "fixed";
                    textArea.style.left = "-9999px";
                    document.body.appendChild(textArea);
                    textArea.focus();
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                    
                    const originalText = button.textContent;
                    button.textContent = 'Copiado!';
                    button.disabled = true;
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.disabled = false;
                    }, 2000);

                } catch (err) {
                    console.warn('Fallback de cópia falhou:', err);
                    alert('Não foi possível copiar a legenda. Tente manualmente.');
                }
            }
        }

        // MODIFICAÇÃO INÍCIO: Lógica para o botão Excluir
        if (target.classList.contains('delete-caption-btn')) {
            const button = target;
            const listItem = button.closest('li'); // Encontra o elemento <li> pai
            if (listItem) {
                listItem.remove(); // Remove o item da lista

                // Opcional: verificar se a lista está vazia e ocultar o título
                if (listaImagens.children.length === 0) {
                    historicoTitulo.style.display = 'none';
                }
            }
        }
    });
});