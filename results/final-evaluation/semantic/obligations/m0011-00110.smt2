(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x471 (= s_6 (_ bv8 4))))
(not $x471)))
(check-sat)
