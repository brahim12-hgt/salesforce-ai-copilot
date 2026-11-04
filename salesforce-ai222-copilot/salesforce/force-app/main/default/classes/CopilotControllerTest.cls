@IsTest
private class CopilotControllerTest {
    private class Mock implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest req) {
            HttpResponse r = new HttpResponse();
            r.setStatusCode(200);
            r.setHeader('Content-Type', 'application/json');
            if (req.getEndpoint().endsWith('/insights')) {
                r.setBody('{"prediction":{"opportunity_id":"x","win_probability":0.3,"loss_risk":0.7,"risk_level":"élevé","priority":1,"factors":[]},"summary":null,"recommendations":[]}');
            } else {
                r.setBody('{"answer":"ok","references":[],"data":[]}');
            }
            return r;
        }
    }

    @IsTest
    static void insightsUpdatesOpportunity() {
        Opportunity o = new Opportunity(Name = 'T', StageName = 'Qualification', CloseDate = Date.today().addDays(30), Amount = 1000);
        insert o;
        Test.setMock(HttpCalloutMock.class, new Mock());
        Test.startTest();
        String res = CopilotController.getInsights(o.Id);
        Test.stopTest();
        System.assert(res.contains('loss_risk'));
        Opportunity r = [SELECT AI_Loss_Risk__c, AI_Priority__c FROM Opportunity WHERE Id = :o.Id];
        System.assertEquals(70, r.AI_Loss_Risk__c);
        System.assertEquals(1, r.AI_Priority__c);
    }

    @IsTest
    static void decisionIsStored() {
        Opportunity o = new Opportunity(Name = 'T', StageName = 'Qualification', CloseDate = Date.today().addDays(30));
        insert o;
        Test.setMock(HttpCalloutMock.class, new Mock());
        Test.startTest();
        CopilotController.recordDecision(o.Id, 'r1', 'Relancer', 'why', 'haute', 'acceptée', null);
        Test.stopTest();
        System.assertEquals(1, [SELECT COUNT() FROM AI_Recommendation__c WHERE Opportunity__c = :o.Id AND Status__c = 'Acceptée']);
    }

    @IsTest
    static void chatReturnsAnswer() {
        Test.setMock(HttpCalloutMock.class, new Mock());
        System.assert(CopilotController.chat('bonjour').contains('answer'));
    }
}
