public with sharing class CopilotController {
    @AuraEnabled
    public static String getInsights(Id recordId) {
        try {
            Map<String, Object> body = new Map<String, Object>{
                'opportunity' => CopilotPayloadBuilder.build(recordId),
                'interactions' => CopilotPayloadBuilder.interactions(recordId)
            };
            String res = CopilotClient.post('/v1/opportunities/' + recordId + '/insights', body);
            persistScore(recordId, res);
            return res;
        } catch (Exception e) {
            throw new AuraHandledException(e.getMessage());
        }
    }

    @AuraEnabled
    public static String getDashboard() {
        try {
            return CopilotClient.get('/v1/dashboard');
        } catch (Exception e) {
            throw new AuraHandledException(e.getMessage());
        }
    }

    @AuraEnabled
    public static String chat(String question) {
        try {
            return CopilotClient.post('/v1/chat', new Map<String, Object>{
                'question' => question, 'user_id' => UserInfo.getUserId()
            });
        } catch (Exception e) {
            throw new AuraHandledException(e.getMessage());
        }
    }

    /** Validation humaine: accepter / modifier / rejeter, tracée côté CRM et côté backend. */
    @AuraEnabled
    public static void recordDecision(Id oppId, String recId, String action, String justification,
                                      String priority, String decision, String modifiedAction) {
        try {
            Set<String> allowed = new Set<String>{ 'acceptée', 'modifiée', 'rejetée' };
            if (!allowed.contains(decision)) {
                throw new AuraHandledException('Décision invalide.');
            }
            insert as user new AI_Recommendation__c(
                Opportunity__c = oppId, Action__c = action.abbreviate(255),
                Justification__c = justification, Priority__c = priority,
                Status__c = decision.capitalize(), Modified_Action__c = modifiedAction,
                Decided_On__c = System.now()
            );
            CopilotClient.post('/v1/decisions', new Map<String, Object>{
                'opportunity_id' => String.valueOf(oppId), 'recommendation_id' => recId,
                'decision' => decision, 'modified_action' => modifiedAction,
                'user_id' => UserInfo.getUserId()
            });
        } catch (Exception e) {
            throw new AuraHandledException(e.getMessage());
        }
    }

    private static void persistScore(Id oppId, String json) {
        Map<String, Object> root = (Map<String, Object>) System.JSON.deserializeUntyped(json);
        Map<String, Object> p = (Map<String, Object>) root.get('prediction');
        String lvl = (String) p.get('risk_level');
        update as user new Opportunity(
            Id = oppId,
            AI_Loss_Risk__c = ((Decimal) p.get('loss_risk')) * 100,
            AI_Risk_Level__c = lvl.capitalize(),
            AI_Priority__c = (Integer) p.get('priority'),
            AI_Last_Scored__c = System.now()
        );
    }
}
