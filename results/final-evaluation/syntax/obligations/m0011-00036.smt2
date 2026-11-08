(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(declare-fun s_4 () (_ BitVec 4))
(assert
 (not (= (ite (= s_4 s_6) (_ bv1 1) (_ bv0 1)) (_ bv1 1))))
(assert
 (let (($x6707 (bvsle s_6 (_ bv15 4))))
(not $x6707)))
(check-sat)
