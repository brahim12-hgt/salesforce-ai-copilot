/**
 * Appelable depuis Salesforce Flow (Record-Triggered Flow sur Opportunity, après création/mise à jour).
 * Le callout est exécuté en asynchrone (Queueable) car un Flow before/after-save ne peut pas appeler directement.
 */
public with sharing class CopilotScoringInvocable {
    @InvocableMethod(label='Score Opportunity with AI Copilot' description='Calcule le risque de perte via le backend IA')
    public static void score(List<Id> opportunityIds) {
        if (!opportunityIds.isEmpty()) {
            System.enqueueJob(new ScoreJob(opportunityIds));
        }
    }

    public class ScoreJob implements Queueable, Database.AllowsCallouts {
        private List<Id> ids;
        public ScoreJob(List<Id> ids) { this.ids = ids; }
        public void execute(QueueableContext ctx) {
            // 1 callout par exécution pour rester sous les limites; le reste est re-chaîné.
            Id first = ids.remove(0);
            try { CopilotController.getInsights(first); } catch (Exception e) { System.debug(LoggingLevel.ERROR, e.getMessage()); }
            if (!ids.isEmpty() && !Test.isRunningTest()) { System.enqueueJob(new ScoreJob(ids)); }
        }
    }
}
