(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(declare-fun s_4 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x2234 (= s_4 s_6)))
(not $x2234)))
(check-sat)
