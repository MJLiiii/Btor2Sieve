(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_3 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x631 (= s_3 (_ bv15 4))))
(not $x631)))
(check-sat)
