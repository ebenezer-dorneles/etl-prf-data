# E-5 — robots.txt do gov.br

- **Date:** 2026-09-19
- **Author:** LLM (Claude Sonnet 5)
- **Question:** O `robots.txt` do gov.br permite acessar a página de dados abertos da PRF?
- **Evidence tier:** scripted
- **Code at:** N/A (projeto sem VCS)

## Environment

Externo, somente leitura, 1 requisição. Autorizado pelo usuário em 2026-09-19.

## Inputs

https://www.gov.br/robots.txt e a URL da página de dados abertos da PRF.

## Reproduce

```
cd docs/specs/prf-acidentes-etl/analysis/explore/E-5-robots
python3 check_robots.py > output.txt
```

Scripts: `check_robots.py` — baixa o robots.txt e usa `urllib.robotparser`.

## Expected output

`output.txt`: `status 200`, nenhuma linha com "prf", `can_fetch ... True` para os dois user-agents.

## Conclusion

O robots.txt não tem regras para `/prf` e permite a página. Confirma a alegação do report §2. Sustenta F-12.

## Supersedes / caveats

Verifica só o robots.txt. Licença/termos do Google Drive e limites de cota não foram verificados (afirmações do report, `reported`); ver Q-6.
