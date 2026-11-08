(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x5011 (= i_2 (_ bv1 4))))
(not $x5011)))
(check-sat)
