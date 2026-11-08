(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x1572 (= s_4 (_ bv15 4))))
(not $x1572)))
(check-sat)
