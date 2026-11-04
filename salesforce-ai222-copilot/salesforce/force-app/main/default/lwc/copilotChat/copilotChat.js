import { LightningElement } from 'lwc';
import chat from '@salesforce/apex/CopilotController.chat';

const SUGGESTIONS = [
    'Quelles opportunités ont le risque de perte le plus élevé ?',
    'Quels clients nécessitent un suivi urgent ?',
    'Quelles sont les principales raisons des échecs commerciaux ?',
    'Quelles opportunités ont le montant le plus élevé ?'
];

export default class CopilotChat extends LightningElement {
    question = '';
    messages = [];
    busy = false;
    nextId = 0;

    get suggestions() { return SUGGESTIONS.map((s) => ({ key: s, text: s })); }
    get noMessages() { return this.messages.length === 0; }
    get disabled() { return this.busy || this.question.trim().length < 2; }

    handleChange(e) { this.question = e.target.value; }
    handleKey(e) { if (e.key === 'Enter' && !this.disabled) this.send(); }
    pick(e) { this.question = e.target.dataset.text; this.send(); }

    push(role, text, refs) {
        this.messages = [...this.messages, {
            key: 'm' + this.nextId++, text, refs: (refs || []).join(', '), hasRefs: !!(refs && refs.length),
            cls: role === 'user' ? 'msg user' : 'msg bot'
        }];
        // eslint-disable-next-line @lwc/lwc/no-async-operation
        setTimeout(() => { const box = this.template.querySelector('.thread'); if (box) box.scrollTop = box.scrollHeight; }, 0);
    }

    async send() {
        const q = this.question.trim();
        this.push('user', q);
        this.question = '';
        this.busy = true;
        try {
            const res = JSON.parse(await chat({ question: q }));
            this.push('bot', res.answer, res.references);
        } catch (e) {
            this.push('bot', e.body?.message || 'Je ne peux pas répondre pour le moment. Réessayez.');
        } finally {
            this.busy = false;
        }
    }
}
