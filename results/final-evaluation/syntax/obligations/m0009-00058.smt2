(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x6209 (= s_6 (_ bv8 4))))
(not $x6209)))
(check-sat)
