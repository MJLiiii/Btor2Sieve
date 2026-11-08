(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_9 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x115 (= i_9 (_ bv255 8))))
(not $x115)))
(check-sat)
