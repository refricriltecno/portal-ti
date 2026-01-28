# Instruções para Adicionar a Logo da Refricril

## O que foi feito:
O sistema foi configurado para exibir a logo da Refricril em dois locais:
1. **Página de Login** - Na parte superior do formulário
2. **Sidebar do Sistema** - No canto superior esquerdo

## Como adicionar a logo:

1. Obtenha o arquivo de logo da Refricril (PNG, SVG ou JPG com fundo transparente é recomendado)

2. Coloque o arquivo na pasta:
   ```
   frontend/src/assets/logo-refricril.png
   ```

3. Se o arquivo tiver um nome diferente, atualize a importação no `App.jsx`:
   ```javascript
   import LogoRefricril from './assets/seu-arquivo-da-logo.png';
   ```

## Recomendações para a logo:
- **Formato**: PNG com fundo transparente (recomendado)
- **Dimensões**: Mínimo 200x100px (será redimensionada automaticamente)
- **Proporção**: Qualquer proporção funciona (mantém aspectRatio)
- **Tamanho do arquivo**: Menos de 500KB

## Tamanhos na interface:
- **Página de Login**: Altura = 80px (h-20 em Tailwind)
- **Sidebar**: Altura = 40px (h-10 em Tailwind)

O sistema redimensionará a logo automaticamente mantendo as proporções.
