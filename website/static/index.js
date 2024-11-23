function removeAcao(acaoId) {
    fetch("/remove-Acao", {
        method: 'POST',
        body: JSON.stringify({acaoId: acaoId}),
    }).then(() => {
        window.location.href="/acoes"
    });
}
function atualizaAcao(acaoId) {
    fetch("/atualiza-Acao", {
        method: 'POST',
        body: JSON.stringify({acaoId: acaoId}),
    }).then(() => {
        window.location.href = "/acoes"
    })
}
function removeCrypto(cryptoId) {
    fetch("/remove-Crypto", {
        method: 'POST',
        body: JSON.stringify({cryptoId: cryptoId}),
    }).then(() => {
        window.location.href="/cryptos"
    });
}
function atualizaCrypto(cryptoId) {
    fetch("/atualiza-Crypto", {
        method: 'POST',
        body: JSON.stringify({cryptoId: cryptoId}),
    }).then(() => {
        window.location.href = "/cryptos"
    })
}
function removeWatchlist(watchlistId) {
    fetch("/remove-watch-list", {
        method: 'POST',
        body: JSON.stringify({watchlistId: watchlistId}),
    }).then(() => {
        window.location.href="/watch-list"
    });
}

// function limitCheckboxSelection(checkbox) {
//     var checkboxes = document.getElementsByName('tipo_operacao');
//     checkboxes.forEach(function(currentCheckbox) {
//         if (currentCheckbox !== checkbox) {
//             currentCheckbox.checked = false;
//         }
//     });
// }